#!/bin/zsh
# usage: setup.sh <project_dir> <youtube_url|local_video>
# Downloads source, detects scene cuts, splits dialogue/music stems. Idempotent (skips finished steps).
set -e
SKILL=${0:A:h:h}
P=${1:?project dir}; SRC=${2:?url or file}
mkdir -p $P/build && cd $P
[ -f $SKILL/assets/gsap.min.js ] || curl -fsSL https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js -o $SKILL/assets/gsap.min.js  # GSAP standard license: fetched, not redistributed
command -v yt-dlp >/dev/null || brew install yt-dlp
python3 -c "import cv2" 2>/dev/null || pip3 install --user -q --break-system-packages opencv-python-headless numpy

if [ ! -f source.mp4 ]; then
  if [ -f "$SRC" ]; then ffmpeg -hide_banner -loglevel error -i "$SRC" -c copy source.mp4
  else yt-dlp -q -f "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[ext=mp4]" --merge-output-format mp4 -o source.mp4 "$SRC"; fi
fi
[ -f scenes.txt ] || ffmpeg -hide_banner -nostats -loglevel error -i source.mp4 -an -vf "scale=480:-2,scdet=threshold=8,metadata=print:file=scenes.txt" -f null -

VENV=~/.cache/recut-venv
if [ ! -x $VENV/bin/python ] || ! $VENV/bin/python -c "import demucs" 2>/dev/null; then
  uv venv -q -p 3.12 $VENV && uv pip install -q -p $VENV/bin/python demucs soundfile
fi
if [ ! -f build/stems/htdemucs/source_audio/vocals.wav ]; then
  ffmpeg -hide_banner -loglevel error -y -i source.mp4 -vn -ac 2 -ar 44100 build/source_audio.wav
  $VENV/bin/python -m demucs --two-stems=vocals -n htdemucs -d mps -o build/stems build/source_audio.wav >/dev/null 2>&1
fi
[ -f project.py ] || cp $SKILL/scripts/project_template.py project.py
ffprobe -v error -show_entries stream=width,height,r_frame_rate:format=duration -of compact source.mp4
echo "scenes: $(grep -c lavfi.scd.time scenes.txt)  stems: ok  -> next: transcript.py"
