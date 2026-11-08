#!/usr/bin/env bash
# A tour of the lk CLI against the self-hosted lab.  Run:  bash cli_tour.sh
# Needs: the lab running (lab/docker-compose.yml) and lk on PATH.
set -euo pipefail
source "$(dirname "$0")/lab.env"
step() { printf '\n$ %s\n' "$*"; "$@"; }

# 1. Save the lab as a named project, so later commands need no flags.
lk project remove lab >/dev/null 2>&1 || true   # make reruns safe
step lk project add lab --url http://127.0.0.1:7880 --api-key "$LIVEKIT_API_KEY" --api-secret "$LIVEKIT_API_SECRET" --default
step lk project list

# 2. Tokens are signed locally. No server call happens here.
step lk token create --join --room demo --identity alice --valid-for 1h

# 3. Rooms: create with timeouts, list, see the HTTP call behind a command.
step lk room create --empty-timeout 120 --departure-timeout 10 demo
step lk room list
step lk room list --curl

# 4. A CLI participant that publishes a demo track, in the background.
lk room join --identity bot --publish-demo demo >/tmp/lk-join.log 2>&1 &
JOIN=$!
sleep 4
step lk room participants list demo
step lk room update --metadata '{"topic":"lab"}' demo
step lk room send-data --room demo --topic chat '{"message":"hello from the cli"}'
step lk room participants update --room demo --permissions '{"can_publish": false, "can_subscribe": true}' bot
sleep 1
step lk room participants get --room demo bot

# 5. Clean up.
kill $JOIN 2>/dev/null || true
step lk room delete demo
