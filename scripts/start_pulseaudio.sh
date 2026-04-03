#!/bin/bash

# Environment for user-instance at boot
export HOME=/root
export XDG_RUNTIME_DIR=/run/user/0
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
mkdir -p "$XDG_RUNTIME_DIR/pulse"
chmod 700 "$XDG_RUNTIME_DIR" 2>/dev/null || true
export PULSE_SERVER=unix:$XDG_RUNTIME_DIR/pulse/native
mkdir -p /root/.config/pulse

# Ensure kernel module is present
modprobe snd-usb-audio 2>/dev/null || true

# PulseAudio starten (nur über boot.pa; verhindert module-udev-detect)
pulseaudio --kill 2>/dev/null || true
pulseaudio -n --daemonize --disallow-exit --log-target=syslog -F /boot/config/plugins/pulseaudio/boot.pa

# Warten bis pactl mit dem laufenden PulseAudio reden kann (Readiness)
for i in {1..30}; do
    if pactl info >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

# Set optimal volume for +4 dBu output (UMC1820 calibrated to Audac R2 input)
pactl set-sink-volume umc1820_master 63%

echo "PulseAudio gestartet via boot.pa"
