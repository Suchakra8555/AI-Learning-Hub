#!/usr/bin/env bash
# Load-test your own server. On self-hosted there is no cap; Cloud limits load-test to 50 per type.
# Run:  bash load_test.sh     (watch CPU with `docker stats lab-livekit-1` in another terminal)
set -euo pipefail
cd "$(dirname "$0")"; source lab.env
ulimit -n 65535 2>/dev/null || true      # the docs ask for this on the machine running the test
lk perf load-test --room load-test --audio-publishers 5 --subscribers 40 --duration 20s
