"""Cheap visual QA without rendering. Writes one JPG to read (instead of many snapshots).
usage:
  python3 qa.py crops           # source frames of no-face shots with crop box drawn -> build/qa_crops.jpg
  python3 qa.py graphics        # bottom band of each segment start/mid -> build/qa_graphics.jpg (find source text/badges/timers to FIT or raise)
  python3 qa.py cut 12.5 97.9   # frames of build/video.mp4 at cut times -> build/qa_cut.jpg
"""
import json, sys, cv2, numpy as np

def grid(tiles, cols, out):
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    cv2.imwrite(out, np.vstack([np.hstack(tiles[k:k + cols]) for k in range(0, len(tiles), cols)]))
    print(out, len(tiles), "tiles")

mode = sys.argv[1]
cap = cv2.VideoCapture("source.mp4"); fps = cap.get(cv2.CAP_PROP_FPS)
def at(c, n):
    c.set(cv2.CAP_PROP_POS_FRAMES, n); return c.read()[1]
if mode == "crops":
    d = json.load(open("build/cut.json")); tiles = []
    for i, p in enumerate(d["pieces"]):
        if p["faces"] or p["fit"]:
            continue
        img = at(cap, (p["sf"] + p["ef"]) // 2); cw, ch, x, y = p["crop"]
        cv2.rectangle(img, (x, y), (x + cw, y + ch), (0, 255, 255), 12)
        cv2.putText(img, f"{i} @{p['sf']/fps:.1f}", (30, 90), 0, 2.5, (0, 0, 255), 6)
        tiles.append(cv2.resize(img, (480, 270)))
    grid(tiles, 4, "build/qa_crops.jpg")
elif mode == "graphics":
    sys.path.insert(0, "."); from project import EDL
    tiles = []
    for a, b, note in EDL:
        for t in (a + 0.3, (a + b) / 2, b - 0.3):
            img = at(cap, round(t * fps)); h = img.shape[0]
            band = cv2.resize(img[int(h * 0.78):, :], (960, 110))
            cv2.putText(band, f"{t:.1f}", (5, 30), 0, 1, (0, 0, 255), 2); tiles.append(band)
    grid(tiles, 3, "build/qa_graphics.jpg")
elif mode == "cut":
    v = cv2.VideoCapture("build/video.mp4"); vf = v.get(cv2.CAP_PROP_FPS); tiles = []
    for t in map(float, sys.argv[2:]):
        img = at(v, round(t * vf)); img = cv2.resize(img, (360, int(360 * img.shape[0] / img.shape[1])))
        cv2.putText(img, f"{t}", (8, 30), 0, 1, (0, 0, 255), 2); tiles.append(img)
    grid(tiles, 4, "build/qa_cut.jpg")
