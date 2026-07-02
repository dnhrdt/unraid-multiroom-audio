#!/usr/bin/env bash
set -euo pipefail

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Environment for a root user-instance at boot.
export HOME=/root
export XDG_RUNTIME_DIR=/run/user/0
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
mkdir -p "$XDG_RUNTIME_DIR/pulse" /root/.config/pulse
chmod 700 "$XDG_RUNTIME_DIR" 2>/dev/null || true
export PULSE_SERVER=unix:$XDG_RUNTIME_DIR/pulse/native

ensure_alsa_lib() {
  if grep -a -q "snd_use_case_mgr_open" /usr/lib64/libasound.so.2 2>/dev/null; then
    return 0
  fi

  local pkg
  pkg=$(ls -1 /boot/extra/alsa-lib-*.txz 2>/dev/null | sort -V | tail -n 1 || true)
  if [[ -z "${pkg}" ]]; then
    log "ERROR: libasound lacks UCM symbols and no /boot/extra/alsa-lib-*.txz package exists"
    exit 1
  fi

  log "Installing ALSA library package: ${pkg}"
  installpkg "${pkg}"
  ldconfig 2>/dev/null || true

  if ! grep -a -q "snd_use_case_mgr_open" /usr/lib64/libasound.so.2 2>/dev/null; then
    log "ERROR: libasound still lacks snd_use_case_mgr_open after installing ${pkg}"
    exit 1
  fi
}

wait_for_umc1820() {
  modprobe snd-usb-audio 2>/dev/null || true

  for _ in {1..30}; do
    if grep -q "UMC1820" /proc/asound/cards 2>/dev/null; then
      return 0
    fi
    sleep 1
  done

  log "ERROR: UMC1820 not present in /proc/asound/cards"
  cat /proc/asound/cards 2>/dev/null || true
  exit 1
}

stop_pulseaudio() {
  pulseaudio --kill 2>/dev/null || true
  sleep 1
  pkill -TERM -x pulseaudio 2>/dev/null || true
  sleep 1
  pkill -KILL -x pulseaudio 2>/dev/null || true
  rm -f "$XDG_RUNTIME_DIR/pulse/pid" "$XDG_RUNTIME_DIR/pulse/native"
}

wait_for_master_sink() {
  for _ in {1..60}; do
    if pactl list sinks short 2>/dev/null | grep -q "umc1820_master"; then
      return 0
    fi
    sleep 1
  done

  log "ERROR: umc1820_master did not appear"
  pactl info 2>&1 || true
  pactl list sinks short 2>&1 || true
  exit 1
}

ensure_alsa_lib
wait_for_umc1820
stop_pulseaudio

# Use boot.pa only; do not load system.pa/module-udev-detect.
pulseaudio -n --daemonize --disallow-exit --log-target=syslog -F /boot/config/plugins/pulseaudio/boot.pa

wait_for_master_sink

# Calibrated to keep the UMC1820 output near +4 dBu for the Audac R2 input.
pactl set-sink-volume umc1820_master 63%

log "PulseAudio started via boot.pa"
