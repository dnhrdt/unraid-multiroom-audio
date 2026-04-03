#!/usr/bin/env bash
set -euo pipefail

export PULSE_SERVER=unix:/run/user/0/pulse/native

# Wait up to 120s for master sink to appear
for i in {1..120}; do
  if pactl list sinks short 2>/dev/null | grep -q "umc1820_master"; then
    break
  fi
  sleep 1
done

# Guard: if master sink still not available, do not start Kodi
if ! pactl list sinks short 2>/dev/null | grep -q "umc1820_master"; then
  echo "umc1820_master not available after wait; aborting Kodi start" >&2
  exit 1
fi

# Start Kodi containers in fixed order with staggering
order=(rot orange gelb gruen blau)
for color in "${order[@]}"; do
  n="kodi-${color}"
  if ! docker ps -a --format '{{.Names}}' | grep -qx "${n}"; then
    echo "${n} not present; skipping"
    continue
  fi
  # Avoid auto-restart before audio is ready
  docker update --restart=no "${n}" >/dev/null 2>&1 || true
  st=$(docker inspect -f '{{.State.Status}}' "${n}" 2>/dev/null || echo unknown)
  case "${st}" in
    running)
      echo "${n} already running; leaving as-is"
      ;;
    paused)
      echo "unpausing ${n}"
      docker unpause "${n}" || true
      ;;
    created|exited)
      echo "starting ${n}"
      docker start "${n}" || true
      ;;
    restarting)
      echo "${n} is restarting; leaving to finish"
      ;;
    *)
      echo "starting ${n} (state=${st})"
      docker start "${n}" || true
      ;;
  esac
  # Stagger start to avoid filesystem contention
  sleep 5
done

exit 0
