"""Transition kinds per segment (applied INTO segment i from i-1). Shared by build.py, captions.py, transition_audit.py."""
KINDS = ("flash", "dip", "whip", "jcut")
JCUT_SEC = 0.35   # picture lags audio at a jcut: next line is heard over the previous shot

def kinds(P, notes):
    table = dict(getattr(P, "TRANSITIONS", {}))
    for sub in getattr(P, "FLASH_AT", []):          # backward compat
        table.setdefault(sub, "flash")
    out = [None]
    for note in notes[1:]:
        k = next((kind for sub, kind in table.items() if sub in note), None)
        if k and k not in KINDS:
            raise SystemExit(f"unknown transition '{k}' (use {KINDS})")
        out.append(k)
    return out
