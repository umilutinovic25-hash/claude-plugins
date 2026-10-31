#!/bin/zsh
# usage: render.sh [output_name]   (inside project dir, after build.py + captions.py)
# Renders ONLY the transparent caption layer in HyperFrames (full video-in-Chrome renders OOM-kill on 16 GB),
# then composites with ffmpeg. Run with Bash run_in_background — takes ~5-10 min for 3 min.
set -e -o pipefail
NAME=${1:-final}
mkdir -p renders
cd overlay
npx hyperframes check 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | grep -E "✗|Check (passed|failed)" | head -8
npx hyperframes render --workers 2 --format mov -o ../build/overlay.mov --fps $(python3 -c "import json;print(json.load(open('../build/segments.json'))['fps_str'])") 2>&1 \
  | sed 's/\x1b\[[0-9;]*m//g' | grep -E "Render complete|rror|Invalid|· " | tail -3
[ -f ../build/overlay.mov ] || { echo "!! overlay render failed"; exit 1; }
cd ..
ffmpeg -hide_banner -loglevel error -y -i build/video.mp4 -i build/overlay.mov -i build/audio.wav \
  -filter_complex "[1:v]format=yuva444p[ov];[0:v][ov]overlay=0:0:format=auto:shortest=1,format=yuv420p[v]" \
  -map "[v]" -map 2:a -c:v libx264 -preset slow -crf 16 -profile:v high -c:a aac -b:a 256k -ar 48000 -movflags +faststart -shortest renders/$NAME.mp4
rm -f build/overlay.mov
ffprobe -v error -show_entries stream=codec_name,width,height:format=duration,size -of compact renders/$NAME.mp4
ffmpeg -hide_banner -nostats -i renders/$NAME.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I:|Peak:)"
ROWS=$(python3 -c "import json,math;print(max(1,math.ceil(json.load(open('build/cut.json'))['duration']/2/10)))")
ffmpeg -hide_banner -loglevel error -y -i renders/$NAME.mp4 -vf "fps=1/2,scale=160:-2,tile=10x$ROWS" -frames:v 1 renders/${NAME}_contact.jpg
echo "DONE -> renders/$NAME.mp4 (review renders/${NAME}_contact.jpg)"
