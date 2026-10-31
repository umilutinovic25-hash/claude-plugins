"""Print word timings for source ranges, to place cut points precisely.
usage: python3 words.py 22-27.5 36.5-44.5
"""
import json, sys
W = json.load(open("words.json"))
for r in sys.argv[1:]:
    a, b = map(float, r.split("-"))
    print(f"== {r}\n" + " ".join(f"{w[2]}@{w[0]:.2f}-{w[1]:.2f}" for w in W if w[0] >= a and w[1] <= b))
