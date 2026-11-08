#!/usr/bin/env bash
# Configure the self-hosted SIP service with lk.  Run:  bash sip_setup.sh
# Needs: docker compose --profile sip up -d   (in lab/), and the echo agent running.
set -euo pipefail
cd "$(dirname "$0")"; source lab.env
step() { printf '\n$ %s\n' "$*"; "$@"; }
step lk sip inbound create sip/inbound-trunk.json
step lk sip dispatch create sip/dispatch-rule.json
step lk sip outbound create sip/outbound-trunk.json
step lk sip inbound list
step lk sip dispatch list
step lk sip outbound list
