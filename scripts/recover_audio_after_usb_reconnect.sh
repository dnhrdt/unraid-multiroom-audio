#!/usr/bin/env bash
set -euo pipefail

export HOME=/root
export XDG_RUNTIME_DIR=/run/user/0
export PULSE_SERVER=unix:/run/user/0/pulse/native
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

colors=(rot orange gelb gruen blau)

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

wait_for_healthy_or_running() {
  local name="$1"
  local state health

  for _ in {1..90}; do
    state=$(docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null || echo missing)
    health=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$name" 2>/dev/null || echo missing)

    if [[ "$state" == "running" && ( "$health" == "healthy" || "$health" == "none" ) ]]; then
      return 0
    fi
    sleep 1
  done

  log "WARN: ${name} did not become healthy; state=${state:-unknown} health=${health:-unknown}"
}

log "Checking UMC1820 USB/ALSA presence"
modprobe snd-usb-audio 2>/dev/null || true
if ! grep -q "UMC1820" /proc/asound/cards 2>/dev/null; then
  log "ERROR: UMC1820 not present in /proc/asound/cards"
  lsusb | grep -i -E "behringer|umc|audio" || true
  cat /proc/asound/cards 2>/dev/null || true
  exit 1
fi

log "Restarting PulseAudio"
bash /boot/config/plugins/pulseaudio/start_pulseaudio.sh

log "Restarting Kodi containers"
for color in "${colors[@]}"; do
  name="kodi-${color}"
  if ! docker ps -a --format '{{.Names}}' | grep -qx "$name"; then
    log "WARN: ${name} does not exist; skipping"
    continue
  fi

  docker update --restart=no "$name" >/dev/null 2>&1 || true
  state=$(docker inspect -f '{{.State.Status}}' "$name" 2>/dev/null || echo missing)
  case "$state" in
    running)
      docker restart "$name" >/dev/null
      ;;
    paused)
      docker unpause "$name" >/dev/null || true
      docker restart "$name" >/dev/null
      ;;
    *)
      docker start "$name" >/dev/null
      ;;
  esac

  log "Restarted ${name}"
  sleep 5
done

log "Waiting for Kodi health checks"
for color in "${colors[@]}"; do
  wait_for_healthy_or_running "kodi-${color}"
done

log "Final PulseAudio state"
pactl list sinks short
pactl list clients short | grep -E 'kodi-x11|pactl' || true
pactl list sink-inputs short

log "Audio recovery complete"
