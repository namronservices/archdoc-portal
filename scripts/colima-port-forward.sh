#!/usr/bin/env bash
# Forward the app's container ports from the Colima VM to the Mac host.
#
# Colima publishes container ports inside its Lima VM and normally tunnels them
# to localhost automatically. If that watcher misses a port (you see
# "This site can't be reached" on http://localhost:5173), run this script to
# add the forwards to Colima's own persistent SSH connection.
#
# Usage:  ./scripts/colima-port-forward.sh
#
# The forwards last for the life of the Colima VM. Re-run after `colima restart`
# or a reboot. A full `colima restart` also re-initialises the auto-forwarder.
set -euo pipefail

CONFIG="$(mktemp -t colima-ssh-config)"
trap 'rm -f "$CONFIG"' EXIT

colima ssh-config > "$CONFIG"

PORTS=(5173 8000)
ARGS=()
for p in "${PORTS[@]}"; do
  ARGS+=(-L "${p}:127.0.0.1:${p}")
done

echo "Forwarding ports ${PORTS[*]} from the Colima VM to localhost..."
# Connects through Colima's ControlMaster; the forwards persist with it.
ssh -F "$CONFIG" -N "${ARGS[@]}" colima &
SSH_PID=$!
sleep 3

for p in "${PORTS[@]}"; do
  if curl -s --max-time 5 -o /dev/null "http://localhost:${p}/" \
     || nc -z 127.0.0.1 "$p" 2>/dev/null; then
    echo "  localhost:${p}  ->  ready"
  else
    echo "  localhost:${p}  ->  NOT reachable"
  fi
done

echo "Done. Open http://localhost:5173"
# The forwards stay attached to Colima's SSH master, so this helper can exit.
kill "$SSH_PID" 2>/dev/null || true
