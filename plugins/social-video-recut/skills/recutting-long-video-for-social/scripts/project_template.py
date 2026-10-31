# Per-project edit. Only this file changes between projects.

# Output frame. Square FB feed: 1080x1080. Reels/Shorts/TikTok: 1080x1920. Landscape: 1920x1080.
OUT_W, OUT_H = 1080, 1080

# (source_in, source_out, note). Seconds in source.mp4. Order = story order (flash-forwards allowed).
# Hook first 3-10 s: premise line + a flash-forward of the stakes. Cut on word edges (words.py), check with edl_check.py.
EDL = [
    # (0.05, 2.72, "HOOK: premise"),
]

# Source ranges whose on-screen graphics are wider than the output crop (title cards, name/subscriber badges,
# full-width text). Shown as full 16:9 frame over a blurred fill instead of cropped.
FIT_RANGES = []

# Detect creator's burned-in bottom captions and blur them (avoids double captions).
BLUR_SOURCE_CAPTIONS = True
# Detect big countdown-timer graphics bottom-left: crop pinned left so they stay whole, captions lifted above them.
DETECT_TIMERS = True

# ---- captions ----
# words the transcript dropped (bleeped / missing): [start, end, "TEXT", speaker] in SOURCE seconds. Verify with whisper.
INSERTS = []
TEXT_FIX = {"1000000.": "MILLION."}          # raw transcript token -> caption text
KEYWORDS = set()                              # UPPERCASE words drawn in accent colour
CAPTION_Y = None                              # top of caption box in px; None = auto per aspect
CAPTION_Y_RAISED = None                       # used while a bottom graphic (timer) is on screen

# ---- overlay graphics (all optional; anchors resolved on the cut timeline) ----
HOOK_TAG = None                               # e.g. "GUINNESS WORLD RECORD ATTEMPT" (shown until HOOK_END_SEGMENT starts)
HOOK_END_SEGMENT = 4                          # index of first non-hook segment
CHIPS = []                                    # [("10 HOURS LATER", "<note substring>", None|"WORD", seconds)]
STAMP = None                                  # ("NEW WORLD RECORD", "25.76 KG", "<note substring>", "25.76", seconds)
# Transitions INTO a segment, keyed by a substring of its note. Default = hard cut.
#   flash: white flash + whoosh   -> jump in time (into a flash-forward tease, and back out of it)
#   dip:   short dip to black      -> new day/location, "hours later" (pair with a CHIP)
#   whip:  blurred slide + whoosh  -> energetic jump between locations in a montage
#   jcut:  next line heard over the previous shot (0.35 s) -> softens a speaker/shot change mid-conversation
# Run the ordering-cuts-and-transitions audit before building.
TRANSITIONS = {}                              # e.g. {"TEASE": "flash", "BACK:": "flash", "5 AM": "dip"}
FLASH_AT = []                                 # legacy alias for {"...": "flash"}
