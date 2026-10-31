---
name: recutting-long-video-for-social
description: Use when turning a long landscape video (YouTube link or file) into a short square or vertical social edit with burned-in captions — Facebook 1:1, Reels/Shorts/TikTok 9:16, "convert this video into a 3-minute edit", video editor test assignments, or when OpusClip/auto-clippers return random clips with no story.
---

# Recutting Long Video for Social

## Overview
An editor's cut: a human-chosen story (EDL written from a word-timed transcript), reframed per shot, captioned, and audio-mixed. Everything except `project.py` is done by tested scripts. **Don't rewrite them; don't use auto-clippers for narrative.**

`S=<this skill's base directory>/scripts`, run inside the project dir.

## Pipeline
| Step | Command | Time |
|---|---|---|
| 1. Fetch, scene cuts, stems | `$S/setup.sh <dir> <url\|file>` | ~1-2 min |
| 2. Transcript | `python3 $S/transcript.py --opus <saved tool-result>` or `--whisper` | secs |
| 3. Read `transcript.txt` (compact) → write `EDL` in `project.py` | `python3 $S/words.py 22-27` for exact word edges | |
| 4. Validate EDL | `python3 $S/edl_check.py` → fix every `!!` | secs |
| 4b. Order & transitions | **REQUIRED:** ordering-cuts-and-transitions → `transition_audit.py` until 0 flags | secs |
| 5. Look for source graphics | `python3 $S/qa.py graphics` → add wide ones to `FIT_RANGES` | secs |
| 6. Build video+audio | `python3 $S/build.py` (Bash `run_in_background`) | 2-7 min |
| 7. QA crops | `python3 $S/qa.py crops` (no-face shots with crop box) | secs |
| 8. Captions + overlays | `python3 $S/captions.py` (re-run alone for caption-only changes) | secs |
| 9. Render | `$S/render.sh final` (`run_in_background`) → read `renders/final_contact.jpg` | 5-10 min |

## Editorial recipe (the part only you do)
- Target length ±2 s. Budget: hook 8-12 s, then setup → complication (the thing that goes wrong) → race/climax → reveal → payoff → one funny button line. Cut tangents, promos, and anything contradicting a later fact.
- Hook = premise → a line that MOTIVATES the jump (a warning, "what could go wrong") → 2-4 s flash-forward of the disaster → back to where you left. Mark tease/return notes and set `TRANSITIONS` (flash/dip/whip/jcut) per ordering-cuts-and-transitions. An unmotivated hard cut into a tease reads as a random mistake.
- Tease shots: no characters or name graphics the viewer hasn't met yet.
- Keep creator's voice: their words only, no reordering within a sentence.
- `INSERTS`: bleeped/dropped words (verify: `whisper-cli` on a 3 s clip). Censor captions the way the creator does ("F#$K").
- Keywords (yellow) = numbers, stakes, names. Hook tag / chips / stamp only where they add info.

## What the scripts already handle (don't re-solve)
| Problem | Handled by |
|---|---|
| Faces off-centre in crop; food shots | YuNet face centroid; gradient-detail fallback |
| Flash frames (<12 f) at cut edges | edges snap to scene cuts without clipping words |
| Jump cut inside same shot | alternating 1.14× punch-in |
| Creator's burned-in captions → double captions | detected + feather-blurred |
| Creator's countdown timers bottom-left | crop pinned left, captions lifted |
| Music jumping at every cut | Demucs stems: dialogue hard-cut, music 240 ms crossfade |
| loudnorm eats ~90 ms tail → A/V mismatch | pts reset + pad + trim |
| Caption shorter than pop tween stays STUCK | flash captions merged; tween ≤ half caption |
| Lines ending "RECORD WITH" | weak words carried to next line |
| Full video render in Chrome OOM-killed (16 GB) | render.sh renders transparent overlay only + ffmpeg composite |
| HyperFrames `Invalid fps` for 29.97 | rational `fps_str` passed |
| Caption hanging over a cut into the next shot | caption end clamped to its segment end |
| Real words with 0.01 s timing dropped ("OFF GO") | only repeated zero-length runs are junk |
| Sliver of source caption at shot edges | blur spans extended to piece edges |

## Verification before handing over
- `build.py` prints `video X audio X` equal; `render.sh` prints ≈ −14 LUFS (clips <60 s read ~−17, fine).
- Read the contact sheet: every tile has one caption, no cropped text/badges, no blank frames. Spot-check with `qa.py cut <t…>` instead of re-rendering.
- 9:16 with creator captions: blurred band sits below captions — set `CAPTION_Y ≈ 0.80*H` if it looks odd.

## Token rules
- Never read raw transcript JSON — only `transcript.txt` / `words.py` ranges.
- One contact sheet per check, not many snapshots. Build/render in background; don't poll.
- Change `project.py` → re-run only the affected step (captions-only changes skip build).

## Hand-off
Ask/tell the user: uncensored profanity in audio (offer bleep), honest time spent and AI-assisted workflow disclosure for job tests; user sends the file (WeTransfer etc.).
