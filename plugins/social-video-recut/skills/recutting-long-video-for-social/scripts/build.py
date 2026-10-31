"""project.py EDL -> build/video.mp4 (reframed, OUT_W x OUT_H) + build/audio.wav (-14 LUFS) + build/cut.json.
Run inside the project dir after setup.sh + transcript.py. ~2-7 min for a 3-min cut (face detection + encode).
"""
import json, subprocess, os, re, sys
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import cv2, numpy as np
sys.path.insert(0, "."); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import project as P
import detectors
from transitions import kinds, JCUT_SEC

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "source.mp4"
probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate", "-of", "json", SRC], capture_output=True, text=True)
st = json.loads(probe.stdout)["streams"][0]
SW, SH, FPS_STR = st["width"], st["height"], st["r_frame_rate"]
FPS = float(Fraction(FPS_STR))
OUT_W, OUT_H = P.OUT_W, P.OUT_H
FIT_RANGES = getattr(P, "FIT_RANGES", [])
SNAP = 12  # frames: min shot length; edges within this of a scene cut snap to it (kills flash frames)
os.makedirs("build/pieces", exist_ok=True)
for f in os.listdir("build/pieces"):
    os.remove(os.path.join("build/pieces", f))

cuts = sorted({round(float(m) * FPS) for m in re.findall(r"lavfi\.scd\.time=([\d.]+)", open("scenes.txt").read())})
WORDS = json.load(open("words.json"))
cap = cv2.VideoCapture(SRC)
det = cv2.FaceDetectorYN.create(os.path.join(SKILL, "assets/yunet.onnx"), "", (960, 540), 0.75, 0.3, 5000)
sx, sy = SW / 960, SH / 540

def frame(n):
    cap.set(cv2.CAP_PROP_POS_FRAMES, n)
    ok, img = cap.read()
    return img

def faces(img):
    _, f = det.detect(cv2.resize(img, (960, 540)))
    return [] if f is None else [(x * sx, y * sy, w * sx, h * sy) for x, y, w, h, *_ in f]

def detail_center(img):
    """no faces (food/product shots): x-centre of visual detail (gradient energy)"""
    g = cv2.GaussianBlur(cv2.cvtColor(cv2.resize(img, (480, 270)), cv2.COLOR_BGR2GRAY), (5, 5), 0)
    mag = cv2.magnitude(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))
    col = np.convolve(mag[27:243].sum(axis=0), np.ones(60) / 60, mode="same")
    return float((col ** 2 * np.arange(480)).sum() / max((col ** 2).sum(), 1e-6)) * SW / 480

def hist(img):
    h = cv2.calcHist([cv2.cvtColor(cv2.resize(img, (320, 180)), cv2.COLOR_BGR2HSV)], [0, 1], None, [32, 32], [0, 180, 0, 256])
    return cv2.normalize(h, h).flatten()

# ---- segments: snap edges to nearby scene cuts, never clipping a word ----
segs = []
for a, b, note in P.EDL:
    sf, ef = round(a * FPS), round(b * FPS)
    head = [c for c in cuts if sf < c <= sf + SNAP]
    if head and not any(sf / FPS - 0.02 <= w[0] < head[-1] / FPS for w in WORDS):
        sf = head[-1]
    tail = [c for c in cuts if ef - SNAP <= c < ef]
    if tail and not any(tail[0] / FPS < w[1] <= ef / FPS + 0.02 for w in WORDS):
        ef = tail[0]
    segs.append({"sf": sf, "ef": ef, "note": note})
TR = kinds(P, [sg["note"] for sg in segs])
# picture edges can differ from audio edges: jcut = previous shot holds while the next line starts
pic = [dict(sg) for sg in segs]
L = round(JCUT_SEC * FPS)
for i, k in enumerate(TR):
    if k != "jcut":
        continue
    a, b = pic[i - 1], pic[i]
    blocked = any(a["ef"] < c <= a["ef"] + L for c in cuts) or any(b["sf"] < c <= b["sf"] + L + SNAP for c in cuts) or b["ef"] - b["sf"] < L + 2 * SNAP
    if blocked:
        print(f"!! jcut into seg {i} skipped (scene cut too close / segment too short) -> use a hard cut or flash")
        TR[i] = None
        continue
    a["ef"] += L; b["sf"] += L
json.dump({"fps": FPS, "fps_str": FPS_STR, "segments": segs, "picture": pic, "transitions": TR}, open("build/segments.json", "w"), indent=1)

# ---- pieces = picture segment ∩ shot ----
pieces = []
for si, sg in enumerate(pic):
    bounds = [sg["sf"]]
    for c in cuts:
        if sg["sf"] < c < sg["ef"] and c - bounds[-1] >= SNAP and sg["ef"] - c >= SNAP:
            bounds.append(c)
    bounds.append(sg["ef"])
    pieces += [{"seg": si, "sf": p0, "ef": p1} for p0, p1 in zip(bounds, bounds[1:])]

def crop_size(zoom):
    if OUT_W / OUT_H <= SW / SH:
        ch = SH / zoom; cw = ch * OUT_W / OUT_H
    else:
        cw = SW / zoom; ch = cw * OUT_H / OUT_W
    return int(cw // 2 * 2), int(ch // 2 * 2)

prev_center, prev_last, prev_zoom = None, None, 1.0
for i, p in enumerate(pieces):
    n = p["ef"] - p["sf"]
    fx = fy = wsum = 0.0
    nf = 0
    for s in (p["sf"] + int(n * r) for r in (0.15, 0.5, 0.85)):
        for x, y, w, h in faces(frame(s)):
            area = w * h; fx += (x + w / 2) * area; fy += (y + h * 0.45) * area; wsum += area; nf += 1
    same_shot = prev_last is not None and float(cv2.compareHist(hist(frame(p["sf"])), prev_last, cv2.HISTCMP_CORREL)) > 0.93
    seg_start = i == 0 or pieces[i - 1]["seg"] != p["seg"]
    zoom = (1.14 if prev_zoom == 1.0 else 1.0) if (seg_start and same_shot) else (1.0 if (seg_start or not same_shot) else prev_zoom)
    if wsum:
        cx, cy = fx / wsum, fy / wsum
    elif same_shot and prev_center:
        cx, cy = prev_center
    else:
        cx, cy = detail_center(frame(p["sf"] + n // 2)), SH / 2
    if same_shot and prev_center and not seg_start and abs(cx - prev_center[0]) < 120:
        cx, cy = prev_center
    p["timer"] = bool(getattr(P, "DETECT_TIMERS", True)) and sum(detectors.timer_graphic((p["sf"] + k) / FPS) for k in range(0, n, 8)) >= max(1, len(range(0, n, 8)) * 0.3)
    if p["timer"]:
        zoom, cx = 1.0, 0
    mid = (p["sf"] + p["ef"]) / 2 / FPS
    p["fit"] = any(a <= mid <= b for a, b in FIT_RANGES)
    cw, ch = crop_size(zoom)
    x = int(min(max(cx - cw / 2, 0), SW - cw)); y = int(min(max(cy - ch / 2, 0), SH - ch))
    p.update(zoom=zoom, crop=[cw, ch, x, y], faces=nf)
    prev_center, prev_zoom, prev_last = (cx, cy), zoom, hist(frame(p["ef"] - 1))

FIT_H = int(OUT_W * SH / SW) // 2 * 2
FIT_Y = (OUT_H - FIT_H) // 2
if getattr(P, "BLUR_SOURCE_CAPTIONS", True):
    for p in pieces:
        cw, ch, x, y = p["crop"]
        spans, box, t = [], None, p["sf"] / FPS
        while t < p["ef"] / FPS:
            bb = detectors.source_caption(t)
            if bb:
                rel = t - p["sf"] / FPS
                if spans and rel - 0.35 <= spans[-1][1]:
                    spans[-1][1] = rel + 0.3
                else:
                    spans.append([max(rel - 0.3, 0), rel + 0.3])
                box = bb if box is None else (min(box[0], bb[0]), min(box[1], bb[1]), max(box[2], bb[2]), max(box[3], bb[3]))
            t += 0.1
        if not box:
            continue
        plen = (p["ef"] - p["sf"]) / FPS
        for sp in spans:  # captions change right at shot edges; don't leave a sliver unblurred
            if sp[0] < 0.45: sp[0] = 0
            if plen - sp[1] < 0.45: sp[1] = plen + 0.1
        if p["fit"]:
            k, ox, oy, lim = OUT_W / SW, 0, -FIT_Y * SW / OUT_W, FIT_Y + FIT_H
        else:
            k, ox, oy, lim = OUT_W / cw, x, y, OUT_H
        bx0 = max(int((box[0] - 50 - ox) * k), 0); by0 = max(int((box[1] - 28 - oy) * k), 0)
        bx1 = min(int((box[2] + 50 - ox) * k), OUT_W); by1 = min(int((box[3] + 28 - oy) * k), lim)
        if bx1 - bx0 > 20 and by1 - by0 > 8:
            p["blur"] = {"box": [bx0, by0, (bx1 - bx0) // 2 * 2, (by1 - by0) // 2 * 2], "spans": [[round(a, 2), round(b, 2)] for a, b in spans]}

for i, p in enumerate(pieces):
    if i + 1 < len(pieces) and pieces[i + 1]["seg"] != p["seg"] and TR[pieces[i + 1]["seg"]] == "whip":
        p["whip_out"] = True
    if i > 0 and pieces[i - 1]["seg"] != p["seg"] and TR[p["seg"]] == "whip":
        p["whip_in"] = True

def encode(i):
    p = pieces[i]
    cw, ch, x, y = p["crop"]
    if p["fit"]:
        vf = (f"fps={FPS_STR},split[s1][s2];[s1]scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,crop={OUT_W}:{OUT_H},"
              f"boxblur=luma_radius=40:luma_power=2,eq=brightness=-0.18:saturation=0.8[bgf];[s2]scale={OUT_W}:{FIT_H}:flags=lanczos[fgf];"
              f"[bgf][fgf]overlay=0:{FIT_Y},setsar=1")
    else:
        xe = str(x)
        d = (p["ef"] - p["sf"]) / FPS
        W_ = 0.14
        amp = int(min(cw * 0.22, max(x, SW - cw - x)))
        sgn = 1 if SW - cw - x >= x else -1
        if p.get("whip_out"):
            xe = f"min(max({x}+{sgn * amp}*clip((t-{d - W_:.3f})/{W_}\\,0\\,1)\\,0)\\,{SW - cw})"
        elif p.get("whip_in"):
            xe = f"min(max({x}-{sgn * amp}*clip(({W_}-t)/{W_}\\,0\\,1)\\,0)\\,{SW - cw})"
        vf = f"crop={cw}:{ch}:'{xe}':{y},scale={OUT_W}:{OUT_H}:flags=lanczos,setsar=1,fps={FPS_STR}"
    if p.get("whip_out"):
        vf += f",boxblur=luma_radius=24:luma_power=2:enable='gte(t,{(p['ef'] - p['sf']) / FPS - 0.14:.3f})'"
    if p.get("whip_in"):
        vf += ",boxblur=luma_radius=24:luma_power=2:enable='lt(t,0.14)'"
    if p.get("blur"):
        bx, by, bw, bh = p["blur"]["box"]
        en = "+".join(f"between(t,{a},{b})" for a, b in p["blur"]["spans"])
        vf += (f",split[m][b];[b]crop={bw}:{bh}:{bx}:{by},boxblur=luma_radius={max(1, min(22, bh // 2 - 1))}:luma_power=3:chroma_radius={max(1, min(10, bh // 4))},"
               f"format=yuva444p,geq=lum='p(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':a='255*clip(min(X\\,W-1-X)/34\\,0\\,1)*clip(min(Y\\,H-1-Y)/18\\,0\\,1)'[bl];"
               f"[m][bl]overlay={bx}:{by}:format=auto:enable='{en}',format=yuv420p")
    out = f"build/pieces/p{i:03d}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{(p['sf'] - 0.5) / FPS:.4f}", "-i", SRC, "-frames:v", str(p["ef"] - p["sf"]), "-an",
                    "-filter_complex", f"[0:v]{vf}", "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p", out], check=True)
    return out

with ThreadPoolExecutor(6) as ex:
    outs = list(ex.map(encode, range(len(pieces))))
open("build/concat.txt", "w").write("".join(f"file 'pieces/{os.path.basename(o)}'\n" for o in outs))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "build/concat.txt", "-c", "copy", "build/video.mp4"], check=True)

# ---- audio: dialogue hard-cut on the frame; music stem crossfaded across cuts; -14 LUFS; exact length ----
STEMS = "build/stems/htdemucs/source_audio"
T = [(sg["sf"] / FPS, sg["ef"] / FPS) for sg in segs]
D = sum(b - a for a, b in T)
n, X = len(T), 0.12
have_stems = os.path.exists(f"{STEMS}/vocals.wav")
inputs = ["-i", f"{STEMS}/vocals.wav", "-i", f"{STEMS}/no_vocals.wav"] if have_stems else ["-i", SRC]
filt = []
for i, (t0, t1) in enumerate(T):
    filt.append(f"[0:a]atrim=start={t0:.5f}:end={t1:.5f},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={t1-t0-0.02:.5f}:d=0.02[v{i}]")
    if have_stems:
        filt.append(f"[1:a]atrim=start={t0 - (X if i else 0):.5f}:end={t1 + (X if i < n - 1 else 0):.5f},asetpts=PTS-STARTPTS[m{i}]")
filt.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1,apad,atrim=end={D:.5f},afade=t=out:st={D-0.08:.5f}:d=0.08[vox]")
mix = "[vox]"
if have_stems:
    prev = "m0"
    for i in range(1, n):
        filt.append(f"[{prev}][m{i}]acrossfade=d={2*X}:c1=qsin:c2=qsin[x{i}]"); prev = f"x{i}"
    filt.append(f"[{prev}]apad,atrim=end={D:.5f},afade=t=out:st={max(D-1.0,0):.5f}:d=1.0[mus]")
    filt.append("[vox][mus]amix=inputs=2:normalize=0:duration=first[mixed]"); mix = "[mixed]"
# loudnorm drops ~90 ms at the tail -> reset pts, pad, trim back to exact length
# whoosh under flash/whip transitions: pink-noise swell peaking on the cut
seg_cut = []
acc = 0.0
for sg in segs:
    seg_cut.append(acc); acc += (sg["ef"] - sg["sf"]) / FPS
flash_t = [seg_cut[i] for i, k in enumerate(TR) if k in ("flash", "whip")]
if flash_t:
    nin = len(inputs) // 2
    inputs += ["-f", "lavfi", "-i", "anoisesrc=d=0.6:c=pink:r=44100:a=0.6,highpass=f=350,lowpass=f=6000,afade=t=in:d=0.42:curve=exp,afade=t=out:st=0.42:d=0.18,aformat=channel_layouts=stereo"]
    filt.append(f"[{nin}:a]asplit={len(flash_t)}" + "".join(f"[w{i}]" for i in range(len(flash_t))))
    for i, t in enumerate(flash_t):
        filt.append(f"[w{i}]adelay={max(0, int((t - 0.42) * 1000))}|{max(0, int((t - 0.42) * 1000))},volume=0.35[wd{i}]")
    filt.append(mix + "".join(f"[wd{i}]" for i in range(len(flash_t))) + f"amix=inputs={len(flash_t)+1}:normalize=0:duration=first[withfx]")
    mix = "[withfx]"
filt.append(f"{mix}loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,asetpts=N/SR/TB,apad,atrim=end={D:.5f}[aout]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filt), "-map", "[aout]", "-c:a", "pcm_s16le", "build/audio.wav"], check=True)

raise_spans, acc = [], 0.0
for p in pieces:
    d = (p["ef"] - p["sf"]) / FPS
    if p["timer"]:
        if raise_spans and abs(raise_spans[-1][1] - acc) < 0.01:
            raise_spans[-1][1] = round(acc + d, 3)
        else:
            raise_spans.append([round(acc, 3), round(acc + d, 3)])
    acc += d
json.dump({"duration": round(D, 3), "raise": raise_spans, "fit_y": [FIT_Y, FIT_H], "pieces": pieces}, open("build/cut.json", "w"), indent=1)
vd = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", "build/video.mp4"], capture_output=True, text=True).stdout)
ad = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", "build/audio.wav"], capture_output=True, text=True).stdout)
print(f"duration {D:.2f}s video {vd:.2f} audio {ad:.2f} | pieces {len(pieces)} fit {sum(p['fit'] for p in pieces)} timer {sum(p['timer'] for p in pieces)} "
      f"blurred {sum(1 for p in pieces if p.get('blur'))} jumpzoom {sum(p['zoom'] > 1 for p in pieces)} noface {sum(not p['faces'] for p in pieces)} stems {have_stems}")
if abs(vd - ad) > 0.05:
    print("!! video/audio length mismatch")
