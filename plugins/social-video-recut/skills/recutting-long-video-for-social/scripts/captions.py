"""words.json + build/segments.json -> overlay/data.js (caption chunks + overlay anchors) and overlay/ project.
Run after build.py. Re-run alone after caption/overlay tweaks in project.py (no rebuild needed).
"""
import json, re, os, sys, shutil
sys.path.insert(0, ".")
import project as P

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
seg = json.load(open("build/segments.json")); FPS = seg["fps"]; SEGS = seg["segments"]
cut = json.load(open("build/cut.json")); DUR = cut["duration"]
W, H = P.OUT_W, P.OUT_H
norm = lambda w: re.sub(r"[.,!?]+$", "", w.upper())
W_ = [w for w in json.load(open("words.json")) if not w[2].startswith("__")] + [list(x) for x in getattr(P, "INSERTS", [])]
W_.sort(key=lambda w: w[0])
# drop only overlap junk: runs of >=3 identical near-zero-length tokens ("No, no, no, no, no").
# Real words can have 0.01 s timings ("you") -> keep them with a minimum length.
junk = set()
for i in range(len(W_)):
    run = [j for j in range(i, min(i + 6, len(W_))) if norm(W_[j][2]) == norm(W_[i][2]) and W_[j][1] - W_[j][0] < 0.03]
    if len(run) >= 3:
        junk.update(run)
W_ = [[w[0], max(w[1], w[0] + 0.05), *w[2:]] for j, w in enumerate(W_) if j not in junk]
FIX = getattr(P, "TEXT_FIX", {}); KEY = {k.upper() for k in getattr(P, "KEYWORDS", set())}

words, off, seg_t = [], 0.0, []
for si, sg in enumerate(SEGS):
    t0, t1 = sg["sf"] / FPS, sg["ef"] / FPS
    seg_t.append(off)
    for s, e, w, *_ in W_:
        if s < t0 - 0.05 or s >= t1 - 0.05:
            continue
        words.append({"w": FIX.get(w, w).upper(), "s": off + max(s - t0, 0), "e": off + min(e, t1) - t0, "seg": si})
    off += (sg["ef"] - sg["sf"]) / FPS

# 1) greedy chunks: <=3 words, <=15 chars, break on sentence end / pause / segment
chunks, cur = [], []
for w in words:
    if cur:
        pv = cur[-1]
        if (w["seg"] != pv["seg"] or w["s"] - pv["e"] > 0.3 or len(cur) >= 3 or sum(len(x["w"]) for x in cur) + len(w["w"]) > 15
                or re.search(r"[.?!]$", pv["w"]) or (pv["w"].endswith(",") and len(cur) >= 2)):
            chunks.append(cur); cur = []
    cur.append(w)
if cur:
    chunks.append(cur)
# 2) never end a line on a function word ("RECORD WITH") -> carry it forward
WEAK = set("A AN THE TO OF IN ON AT FOR WITH AND BUT OR MY OUR YOUR HIS THEM THIS THAT BE IS WAS ARE GONNA WE I YOU IT'S WE'RE I'LL WE'LL".split())
for i in range(len(chunks) - 1):
    a, b = chunks[i], chunks[i + 1]
    while (len(a) > 1 and norm(a[-1]["w"]) in WEAK and not re.search(r"[.?!,]$", a[-1]["w"]) and a[-1]["seg"] == b[0]["seg"]
           and b[0]["s"] - a[-1]["e"] < 0.3 and len(b) < 4 and sum(len(x["w"]) for x in b) + len(a[-1]["w"]) <= 18):
        b.insert(0, a.pop())
chunks = [c for c in chunks if c]
# 3) merge flash captions (<0.3 s). A caption shorter than its pop-in tween gets STUCK on screen in GSAP.
changed = True
while changed:
    changed = False
    for i, ch in enumerate(chunks):
        if (chunks[i + 1][0]["s"] if i + 1 < len(chunks) else DUR) - ch[0]["s"] >= 0.3:
            continue
        if i + 1 < len(chunks) and chunks[i + 1][0]["seg"] == ch[-1]["seg"] and len(chunks[i + 1]) + len(ch) <= 4:
            chunks[i + 1] = ch + chunks[i + 1]
        elif i > 0 and chunks[i - 1][-1]["seg"] == ch[0]["seg"] and len(chunks[i - 1]) + len(ch) <= 4:
            chunks[i - 1] += ch
        else:
            continue
        del chunks[i]; changed = True; break

raise_spans = cut["raise"]
caps = []
for i, c in enumerate(chunks):
    s = c[0]["s"]; nxt = chunks[i + 1][0]["s"] if i + 1 < len(chunks) else DUR
    seg_end = seg_t[c[-1]["seg"]] + (SEGS[c[-1]["seg"]]["ef"] - SEGS[c[-1]["seg"]]["sf"]) / FPS
    e = max(min(nxt, c[-1]["e"] + 0.4, DUR, seg_end), min(s + 0.35, nxt, seg_end))  # never hang over a cut
    caps.append({"s": round(s, 3), "e": round(e, 3), "hi": any(a - 0.05 <= s < b for a, b in raise_spans),
                 "w": [{"t": x["w"] if x["w"].endswith("...") else x["w"].rstrip(",."), "k": norm(x["w"]) in KEY} for x in c]})

def anchor(note_part, word=None):
    si = next(i for i, sg in enumerate(SEGS) if note_part in sg["note"])
    if word is None:
        return round(seg_t[si], 3)
    return round(next(x["s"] for x in words if x["seg"] == si and norm(x["w"]) == word.upper()), 3)

def seg_end_of(note_part):  # overlays never survive into the next scene
    si = next(i for i, sg in enumerate(SEGS) if note_part in sg["note"])
    return seg_t[si] + (SEGS[si]["ef"] - SEGS[si]["sf"]) / FPS

aspect = W / H
cap_y = P.CAPTION_Y or int(H * (0.824 if aspect >= 0.99 else 0.66))
cap_y_hi = P.CAPTION_Y_RAISED or int(cap_y - H * 0.21)
ovl = {"W": W, "H": H, "duration": DUR, "capY": cap_y, "capYHi": cap_y_hi, "fontPx": int(W * 0.0685),
       "hook": [P.HOOK_TAG, round(seg_t[min(P.HOOK_END_SEGMENT, len(seg_t) - 1)], 3)] if getattr(P, "HOOK_TAG", None) else None,
       "chips": [{"text": t, "s": anchor(n, w), "d": min(d, seg_end_of(n) - anchor(n, w) - 0.25)} for t, n, w, d in getattr(P, "CHIPS", [])],
       "stamp": None,
       "transitions": [{"t": round(seg_t[i], 3), "kind": k} for i, k in enumerate(seg.get("transitions", [])) if k in ("flash", "dip")]}
if getattr(P, "STAMP", None):
    lbl, big, n, w, d = P.STAMP
    ovl["stamp"] = {"label": lbl, "text": big, "s": anchor(n, w), "d": d}

os.makedirs("overlay/assets", exist_ok=True)
for f in ("gsap.min.js", "Montserrat-Black.ttf"):
    shutil.copy(os.path.join(SKILL, "assets", f), "overlay/assets/" + f)
tpl = open(os.path.join(SKILL, "overlay-template/index.html")).read()
open("overlay/index.html", "w").write(tpl.replace("__W__", str(W)).replace("__H__", str(H)).replace("__DUR__", str(DUR)))
open("overlay/data.js", "w").write("window.CAPS=" + json.dumps(caps) + ";\nwindow.OVL=" + json.dumps(ovl) + ";\n")
short = [c for c in caps if c["e"] - c["s"] < 0.2]
print(f"{len(caps)} captions, dur {DUR}s, raised {sum(c['hi'] for c in caps)}, <0.2s {len(short)}")
for c in caps[:8]:
    print(f"  {c['s']:6.2f}-{c['e']:6.2f} " + " ".join(("*" if w["k"] else "") + w["t"] for w in c["w"]))
