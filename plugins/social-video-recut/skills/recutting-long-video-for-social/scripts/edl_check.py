"""Validate project.py EDL BEFORE building: running total, clipped words at edges, leaked words from neighbours.
usage: python3 edl_check.py
"""
import json, sys
sys.path.insert(0, ".")
from project import EDL
W = [w for w in json.load(open("words.json")) if not w[2].startswith("__")]
tot, bad = 0.0, 0
for a, b, note in EDL:
    tot += b - a
    inside = [w for w in W if a - 0.05 <= w[0] < b - 0.05]
    flags = []
    if inside and inside[-1][1] > b + 0.02:
        flags.append(f"END clips '{inside[-1][2]}' (ends {inside[-1][1]:.2f})")
    if inside and inside[0][0] < a:
        flags.append(f"START clips '{inside[0][2]}' (starts {inside[0][0]:.2f})")
    before = [w for w in W if w[0] < a - 0.05]
    if before and before[-1][1] > a + 0.02:
        flags.append(f"PREV word '{before[-1][2]}' bleeds in (ends {before[-1][1]:.2f})")
    bad += bool(flags)
    first = inside[0][2] if inside else "-"
    last = inside[-1][2] if inside else "-"
    print(f"{tot:7.2f} +{b-a:5.2f}  {a:7.2f}-{b:7.2f}  [{first} … {last}]  {note}  {'  !! ' + '; '.join(flags) if flags else ''}")
print(f"TOTAL {tot:.2f}s  segments {len(EDL)}  problems {bad}")
