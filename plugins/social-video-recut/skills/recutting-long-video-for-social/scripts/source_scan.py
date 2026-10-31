"""One decode pass over source.mp4 (10 fps, 960x540) -> build/source_scan.json.
Finds creator graphics BEFORE editing: burned-in captions, countdown timers, text graphics (badges, labels, titles),
plus a luma timeline. build.py reads it (no per-piece re-detection) and auto-fits shots whose graphics don't fit the crop.
usage: python3 source_scan.py   (~1 min per 10 min of source; cached, re-runs only if source changed)
"""
import json, os, subprocess, sys
import cv2, numpy as np

SRC, OUT, SFPS, W, H = "source.mp4", "build/source_scan.json", 10, 960, 540
os.makedirs("build", exist_ok=True)
st = os.stat(SRC)
if os.path.exists(OUT):
    old = json.load(open(OUT))
    if old.get("src_size") == st.st_size:
        print("source_scan: cached"); sys.exit(0)
probe = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", SRC], capture_output=True, text=True).stdout)["streams"][0]
SW = probe["width"]; K = SW / W  # multiply scan coords by K -> source px

def caption(img):
    band = img[450:535, 150:810].astype(np.int16)
    bright = (band.min(axis=2) > 215) | ((band[:, :, 2] > 200) & (band[:, :, 1] > 170) & (band[:, :, 0] < 100))
    dark = cv2.dilate((band.max(axis=2) < 45).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    ys, xs = np.nonzero(bright & dark)
    if len(xs) < 200:
        return None
    x0, y0, x1, y1 = xs.min() + 150, ys.min() + 450, xs.max() + 150, ys.max() + 450
    reg = img[y0:y1 + 1, x0:x1 + 1]
    fill = float((reg.min(axis=2) > 215).mean()) if reg.size else 0
    if abs((x0 + x1) / 2 - W / 2) > 80 or not (506 <= y1 <= 523) or fill > 0.6 or x1 - x0 > 725 or y1 - y0 < 15:
        return None
    return [int(v * K) for v in (x0, y0, x1, y1)]

def timer(img):
    """countdown timer bottom-left: big dark box with white digits (or orange 'fire' digits)"""
    reg = img[420:530, 10:260]
    hsv = cv2.cvtColor(reg, cv2.COLOR_BGR2HSV)
    dark = (reg.max(axis=2) < 30).mean(); white = (reg.min(axis=2) > 225).mean()
    orange = ((hsv[:, :, 0] >= 5) & (hsv[:, :, 0] <= 25) & (hsv[:, :, 1] > 170) & (hsv[:, :, 2] > 200)).mean()
    edges = cv2.Canny(cv2.cvtColor(reg, cv2.COLOR_BGR2GRAY), 80, 200).mean() / 255
    # white label boxes ("TEAM 2 THE MEAT") have white~0.5/dark~0.3 -> not timers
    return bool(edges > 0.05 and ((dark > 0.5 and 0.1 < white < 0.4) or (dark > 0.25 and orange > 0.03)))

def text_graphic(img):
    """any bright, sharp-edged text graphic in the lower 40% (name/subscriber badges, team labels, title cards,
    full-width text). Returns bbox in source px or None. Calibrated: 9/9 positives, 0 false hits on 16 negatives."""
    band = img[360:535]
    gray = cv2.cvtColor(band, cv2.COLOR_BGR2GRAY)
    bright = gray > 222
    if bright.mean() > 0.45:                       # white kitchen/counter, not a graphic
        return None
    tl = bright & (cv2.dilate(cv2.Canny(gray, 90, 220), np.ones((3, 3), np.uint8)) > 0)
    cols = np.nonzero(tl.sum(axis=0) >= 3)[0]
    if len(cols) < 60:
        return None
    runs, s0, pv = [], cols[0], cols[0]
    for c in cols[1:]:
        if c - pv > 30:
            runs.append((s0, pv)); s0 = c
        pv = c
    runs.append((s0, pv))
    x0, x1 = max(runs, key=lambda r: tl[:, r[0]:r[1] + 1].sum())
    n = int(tl[:, x0:x1 + 1].sum())
    if x1 - x0 < 200 or n < 1500:
        return None
    rows = np.nonzero(tl[:, x0:x1 + 1].sum(axis=1) >= 2)[0]
    return [int(v * K) for v in (x0, rows.min() + 360, x1, rows.max() + 360)]

proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-vf", f"fps={SFPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
samples, i = [], 0
while True:
    buf = proc.stdout.read(W * H * 3)
    if len(buf) < W * H * 3:
        break
    img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    s = {"t": round(i / SFPS, 2), "l": round(float(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).mean()), 1)}
    c = caption(img); tm = timer(img)
    tg = None if (c or tm) else text_graphic(img)
    if c: s["cap"] = c
    if tm: s["timer"] = 1
    if tg: s["text"] = tg
    samples.append(s); i += 1
proc.wait()

def spans(key, min_len=0.3):
    out, cur = [], None
    for s in samples:
        if key in s:
            if cur and s["t"] - cur[1] <= 0.25: cur[1] = s["t"]
            else:
                if cur and cur[1] - cur[0] >= min_len: out.append(cur)
                cur = [s["t"], s["t"]]
    if cur and cur[1] - cur[0] >= min_len: out.append(cur)
    return [[round(a, 1), round(b + 1 / SFPS, 1)] for a, b in out]

summary = {k: spans(k, 0.5 if k == "text" else 0.3) for k in ("cap", "timer", "text")}
# one image to eyeball every text graphic span (mid frame, bbox drawn) -> confirm FIT_RANGES in a single look
cap_ = cv2.VideoCapture(SRC); vfps = cap_.get(cv2.CAP_PROP_FPS); tiles = []
for a, b in summary["text"][:40]:
    m = (a + b) / 2
    smp = min(samples, key=lambda x: abs(x["t"] - m))
    cap_.set(cv2.CAP_PROP_POS_FRAMES, round(m * vfps)); ok, im = cap_.read()
    if not ok or "text" not in smp:
        continue
    x0, y0, x1, y1 = smp["text"]
    cv2.rectangle(im, (x0, y0), (x1, y1), (0, 255, 255), 8)
    cv2.putText(im, f"{a}-{b}", (20, 80), 0, 2.5, (0, 0, 255), 6)
    tiles.append(cv2.resize(im, (384, 216)))
if tiles:
    while len(tiles) % 5: tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite("build/scan_graphics.jpg", np.vstack([np.hstack(tiles[k:k + 5]) for k in range(0, len(tiles), 5)]))
json.dump({"src_size": st.st_size, "fps": SFPS, "samples": samples, "spans": summary}, open(OUT, "w"))
print(f"source_scan: {len(samples)} samples | " + " | ".join(f"{k}: {len(v)} spans" for k, v in summary.items()))
print("  review build/scan_graphics.jpg (one tile per text graphic)")
for k in ("timer", "text"):
    print(f"  {k}: " + ", ".join(f"{a}-{b}" for a, b in summary[k][:25]))
