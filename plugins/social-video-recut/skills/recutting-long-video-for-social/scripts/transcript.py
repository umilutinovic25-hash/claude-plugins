"""Word-level transcript -> words.json [[start,end,word,speaker],...] + compact transcript.txt (read THIS, never the raw JSON).

usage (run inside project dir):
  python3 transcript.py --opus <saved opusclip_get_transcript output .txt/.json>
  python3 transcript.py --whisper [--model ~/.jarvis/models/ggml-base.en.bin]
"""
import argparse, json, os, subprocess, re

ap = argparse.ArgumentParser()
ap.add_argument("--opus")
ap.add_argument("--whisper", action="store_true")
ap.add_argument("--model", default=os.path.expanduser("~/.jarvis/models/ggml-base.en.bin"))
a = ap.parse_args()

W = []
if a.opus:
    d = json.load(open(a.opus))
    for p in d["paragraphs"]:
        for w in p["words"]:
            t = w["word"].strip()
            if not t.startswith("__"):
                W.append([w["start_ms"] / 1000, w["end_ms"] / 1000, t, str(p.get("speaker", "?"))[-1]])
elif a.whisper:
    os.makedirs("build", exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", "source.mp4", "-ar", "16000", "-ac", "1", "build/whisper.wav"], check=True)
    subprocess.run(["whisper-cli", "-m", a.model, "-f", "build/whisper.wav", "-ml", "1", "-sow", "-ojf", "-of", "build/whisper", "-np"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for seg in json.load(open("build/whisper.json"))["transcription"]:
        t = seg["text"].strip()
        if t and not re.fullmatch(r"\[.*\]|\(.*\)", t):
            W.append([seg["offsets"]["from"] / 1000, seg["offsets"]["to"] / 1000, t, "?"])
else:
    ap.error("--opus or --whisper")

json.dump(W, open("words.json", "w"))
# compact sentence lines: "[start-end] spk: text"
lines, cur = [], []
for w in W:
    if cur and (w[0] - cur[-1][1] > 0.6 or w[3] != cur[-1][3]):
        lines.append(cur); cur = []
    cur.append(w)
    if re.search(r"[.?!]$", w[2]):
        lines.append(cur); cur = []
if cur:
    lines.append(cur)
open("transcript.txt", "w").write("\n".join(f"[{l[0][0]:6.1f}-{l[-1][1]:6.1f}] {l[0][3]}: {' '.join(x[2] for x in l)}" for l in lines))
print(len(W), "words,", len(lines), "lines -> transcript.txt")
