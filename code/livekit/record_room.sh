#!/usr/bin/env bash
# Record a room to a local file with the self-hosted egress service.  Run:  bash record_room.sh
# Needs: docker compose --profile egress up -d  (in lab/), ffmpeg, lk.
set -euo pipefail
cd "$(dirname "$0")"; source lab.env
step() { printf '\n$ %s\n' "$*"; "$@"; }

chmod a+w lab/recordings   # the egress container writes the file as root

# Something to record: a CLI participant publishing 20 s of a 440 Hz tone (Opus in Ogg).
ffmpeg -nostdin -loglevel error -y -f lavfi -i sine=frequency=440:duration=20 -c:a libopus /tmp/tone.ogg
lk room join --identity speaker --publish /tmp/tone.ogg record-me >/tmp/lk-speaker.log 2>&1 &
SPEAKER=$!
sleep 3

step lk egress start egress/room-audio.json | tee /tmp/egress-start.txt
EGRESS_ID=$(grep -o 'EG_[A-Za-z0-9]*' /tmp/egress-start.txt | head -1)
sleep 10
step lk egress list --room record-me
step lk egress stop --id "$EGRESS_ID"
sleep 3
kill $SPEAKER 2>/dev/null || true
step ls -la lab/recordings/
f=$(ls -t lab/recordings/*.ogg | head -1)
step ffprobe -v error -show_entries format=duration:stream=codec_name,sample_rate,channels -of default=nw=1 "$f"
