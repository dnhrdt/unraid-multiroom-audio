# PulseAudio Multi-Room Audio Architecture for Unraid

**Version:** 1.0
**Date:** 2025-11-24
**Author:** Michael

## Overview

This document describes a working architecture for running PulseAudio on Unraid to provide multi-room audio for multiple Kodi headless containers. The solution uses a USB multi-channel audio interface (Behringer UMC1820) and PulseAudio's remap-sink feature to create independent virtual audio outputs for each room.

## Use Case

**Goal:** Synchronized multi-room audio playback with independent volume control per room.

**Hardware:**
- Unraid Server (host)
- Behringer UMC1820 USB audio interface (12 channels, 48kHz, S24LE)
- AudacR2 Audio Matrix (downstream, receives all 10 audio channels)
- 5 rooms with independent audio zones

**Software:**
- 5 Kodi headless Docker containers (one per room)
- PulseAudio 17.0 (running on Unraid host)
- Custom PulseAudio configuration for channel mapping

## Architecture

### Signal Path

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Kodi         │────▶│ PulseAudio   │────▶│  UMC1820     │────▶│  AudacR2     │
│ Container    │ TCP │ Remap Sink   │ USB │  (12ch)      │ TRS │  Matrix      │
│ (Room 1-5)   │4713 │ Master Sink  │     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

### Component Details

**1. Kodi Containers (5 instances)**
- Names: `kodi-rot`, `kodi-orange`, `kodi-gelb`, `kodi-gruen`, `kodi-blau`
- Base Image: Custom (based on `fhriley/kodi-headless-novnc:Omega`)
- Network: Macvlan on VLAN 2 (Media)
- Environment Variables:
  - `PULSE_SERVER=10.0.0.44` (Unraid host IP)
  - `PULSE_SINK=kodi_[color]` (assigned virtual sink)
- Restart Policy: `no` (controlled by startup script)

**2. PulseAudio Server (Host)**
- Instance: User-mode (running as root, `XDG_RUNTIME_DIR=/run/user/0`)
- Configuration: Declarative via `boot.pa`
- Protocols:
  - Unix Socket: `/run/user/0/pulse/native` (local access)
  - TCP: Port 4713 (ACL: `10.2.0.0/24;127.0.0.1`)
- Sinks:
  - 1 Master Sink: `umc1820_master` (12ch, S24LE, 48kHz) → hardware `hw:0,0`
  - 5 Remap Sinks: `kodi_rot`, `kodi_orange`, `kodi_gelb`, `kodi_gruen`, `kodi_blau` (stereo pairs)

**3. Channel Mapping**

| Room/Color | Remap Sink    | Master Channels      | UMC1820 Hardware Channels |
|------------|---------------|----------------------|---------------------------|
| Rot        | kodi_rot      | front-left, front-right | Ch 0-1 (Analog Out 1-2) |
| Orange     | kodi_orange   | rear-left, rear-right   | Ch 2-3 (Analog Out 3-4) |
| Gelb       | kodi_gelb     | front-center, lfe       | Ch 4-5 (Analog Out 5-6) |
| Grün       | kodi_gruen    | side-left, side-right   | Ch 6-7 (Analog Out 7-8) |
| Blau       | kodi_blau     | aux0, aux1              | Ch 8-9 (ADAT 1-2)       |

## File Structure

```
/boot/config/plugins/pulseaudio/
├── boot.pa                       # PulseAudio module configuration (declarative)
├── client.conf                   # PulseAudio client config (autospawn=no)
├── daemon.conf                   # PulseAudio daemon config (exit-idle-time=-1)
├── start_pulseaudio.sh           # PA startup wrapper
└── start_kodi_after_audio.sh     # Kodi staggered start script

/boot/config/plugins/user.scripts/scripts/pulseaudio_for_kodi/
└── script                        # Orchestrator script (triggered by User Scripts Plugin)

/boot/extra/
├── alsa-lib-1.2.14-x86_64-1.txz         # Complete ALSA library (with UCM)
└── sound-20251022-6.12.54-Unraid-1.txz  # Kernel-matched sound drivers
```

## Configuration Files

### 1. `boot.pa` - PulseAudio Module Configuration

```
#!/usr/bin/pulseaudio -nF

# Protocol sockets
load-module module-native-protocol-unix
load-module module-native-protocol-tcp auth-ip-acl="10.2.0.0/24;127.0.0.1" port=4713

# Master ALSA sink (UMC1820 hardware)
load-module module-alsa-sink device=hw:0,0 sink_name=umc1820_master channels=12 format=s24le rate=48000

# Remapped stereo sinks for Kodi (one per room)
load-module module-remap-sink sink_name=kodi_rot master=umc1820_master channels=2 master_channel_map=front-left,front-right channel_map=front-left,front-right remix=no
load-module module-remap-sink sink_name=kodi_orange master=umc1820_master channels=2 master_channel_map=rear-left,rear-right channel_map=front-left,front-right remix=no
load-module module-remap-sink sink_name=kodi_gelb master=umc1820_master channels=2 master_channel_map=front-center,lfe channel_map=front-left,front-right remix=no
load-module module-remap-sink sink_name=kodi_gruen master=umc1820_master channels=2 master_channel_map=side-left,side-right channel_map=front-left,front-right remix=no
load-module module-remap-sink sink_name=kodi_blau master=umc1820_master channels=2 master_channel_map=aux0,aux1 channel_map=front-left,front-right remix=no
```

**Key Points:**
- **Declarative configuration:** All modules loaded via `boot.pa`, no runtime `pactl` commands needed
- **Avoids conflicts:** No `module-udev-detect` or `module-alsa-card` (which can lock hardware)
- **Direct hardware access:** `module-alsa-sink` with `device=hw:0,0`

### 2. `client.conf` - PulseAudio Client Configuration

```
autospawn = no
```

**Purpose:** Prevents PulseAudio from auto-spawning when clients connect. The server is managed explicitly by our startup script.

### 3. `daemon.conf` - PulseAudio Daemon Configuration

```
exit-idle-time = -1
realtime-scheduling = yes
realtime-priority = 5
default-sample-rate = 48000
default-sample-format = s16le
default-sample-channels = 10
remixing-use-all-sink-channels = yes
```

**Key Settings:**
- `exit-idle-time = -1`: Server never exits when idle (important for always-on setup)
- `default-sample-rate = 48000`: Matches UMC1820 hardware
- `default-sample-channels = 10`: Reflects actual channel usage

### 4. `start_pulseaudio.sh` - PA Startup Wrapper

```bash
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

# PulseAudio starten (nur über boot.pa)
pulseaudio --kill 2>/dev/null || true
pulseaudio -n --daemonize --disallow-exit --log-target=syslog -F /boot/config/plugins/pulseaudio/boot.pa

# Warten bis pactl mit dem laufenden PulseAudio reden kann (Readiness)
for i in {1..30}; do
    if pactl info >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

echo "PulseAudio gestartet via boot.pa"
```

**Key Points:**
- Sets up user-instance environment (`XDG_RUNTIME_DIR`)
- Loads kernel module (`snd-usb-audio`)
- Starts PA with `-F boot.pa` (loads configuration file)
- Waits for readiness (up to 30s)

### 5. `start_kodi_after_audio.sh` - Kodi Staggered Start

```bash
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
```

**Key Points:**
- Waits for PA sinks (up to 120s)
- Guard clause: aborts if sinks not available
- Staggered start: 5s delay between containers (prevents playlist filesystem contention)
- Sets restart-policy to `no` (prevents Docker auto-restart before PA ready)

### 6. User Scripts Orchestrator

```bash
#!/bin/bash
set -euo pipefail

export HOME=/root
export XDG_RUNTIME_DIR=/run/user/0
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PULSE_SERVER=unix:/run/user/0/pulse/native

# Copy configs to /etc/pulse/ (transient)
mkdir -p /etc/pulse
cp -f /boot/config/plugins/pulseaudio/client.conf /etc/pulse/client.conf || true
if [ -f /boot/config/plugins/pulseaudio/daemon.conf ]; then
  cp -f /boot/config/plugins/pulseaudio/daemon.conf /etc/pulse/daemon.conf || true
fi

# Start PulseAudio (ABSOLUTE PATH)
bash -x /boot/config/plugins/pulseaudio/start_pulseaudio.sh >>/var/log/pa_start.log 2>&1

# Wait for PA sinks ready
for i in {1..60}; do
  if pactl list sinks short 2>/dev/null | grep -q "umc1820_master"; then
    break
  fi
  sleep 1
done

# Guard: abort if sinks missing
if ! pactl list sinks short 2>/dev/null | grep -q "umc1820_master"; then
  exit 1
fi

# Start Kodi containers (ABSOLUTE PATH)
timeout 240 bash -x /boot/config/plugins/pulseaudio/start_kodi_after_audio.sh >>/var/log/kodi_start.log 2>&1 || true

exit 0
```

**Critical:** Use **absolute paths** for script calls. User Scripts Plugin runs scripts from `/tmp/user.scripts/tmpScripts/`, so relative paths will fail.

## Setup Instructions

### Prerequisites

1. **Install User Scripts Plugin:**
   - Unraid Web UI → Plugins → Install "User Scripts" plugin

2. **Install Required Packages:**
   - Download to `/boot/extra/`:
     - `alsa-lib-1.2.14-x86_64-1.txz` from [Slackware Current](https://slackware.uk/slackware/slackware64-current/slackware64/l/)
     - `sound-[date]-[kernel]-Unraid-1.txz` from [ich777 GitHub](https://github.com/ich777/unraid-sound-driver/releases) (match your kernel version: `uname -r`)
   - Packages auto-install at boot from `/boot/extra/`

### Step-by-Step Setup

1. **Create Directory Structure:**
   ```bash
   mkdir -p /boot/config/plugins/pulseaudio
   mkdir -p /boot/config/plugins/user.scripts/scripts/pulseaudio_for_kodi
   ```

2. **Deploy Configuration Files:**
   - Copy all configuration files to `/boot/config/plugins/pulseaudio/`:
     - `boot.pa`
     - `client.conf`
     - `daemon.conf`
     - `start_pulseaudio.sh`
     - `start_kodi_after_audio.sh`
   - Make scripts executable:
     ```bash
     chmod +x /boot/config/plugins/pulseaudio/*.sh
     ```

3. **Create User Script:**
   - Web UI → Settings → User Scripts → Add New Script → Name: `pulseaudio_for_kodi`
   - Paste orchestrator script content (see section 6 above)
   - Schedule: "At Startup of Array"

4. **Configure Kodi Containers:**
   - Set environment variables in Portainer:
     - `PULSE_SERVER=<unraid-host-ip>` (e.g., `10.0.0.44`)
     - `PULSE_SINK=kodi_[color]` (e.g., `kodi_rot`)
   - Set Restart Policy: `no` (controlled by script)

5. **Test:**
   - Reboot Unraid
   - Verify after boot:
     ```bash
     # Check PA running
     pgrep -a pulseaudio

     # Check sinks (expect 6: 1 master + 5 remaps)
     export XDG_RUNTIME_DIR=/run/user/0
     export PULSE_SERVER=unix:$XDG_RUNTIME_DIR/pulse/native
     pactl list sinks short

     # Check Kodi containers
     docker ps --format '{{.Names}}  {{.Status}}' | grep kodi
     ```

## Troubleshooting

### PA Doesn't Start at Boot

**Symptom:** After reboot, `pgrep pulseaudio` returns nothing, no sinks exist.

**Common Causes:**
1. **User Script uses relative paths:** User Scripts run from `/tmp/user.scripts/tmpScripts/`. Solution: Use absolute paths in orchestrator script.
2. **Packages not installed:** Check `/var/log/packages/alsa-lib*` and `/var/log/packages/sound-*`. Ensure correct versions in `/boot/extra/`.
3. **Kernel module mismatch:** `sound-*.txz` version must match `uname -r`. Download matching version from ich777 GitHub.

**Debug:**
```bash
# Check User Script logs
tail -n 100 /var/log/pa_start.log
tail -n 100 /var/log/kodi_start.log

# Manual test
bash -x /boot/config/plugins/pulseaudio/start_pulseaudio.sh
```

### ALSA Symbol Errors

**Symptom:** `undefined symbol: snd_use_case_mgr_open, version ALSA_0.9`

**Cause:** Stripped `alsa-lib` package missing UCM subsystem.

**Solution:** Use official Slackware Current `alsa-lib-1.2.14-x86_64-1.txz` (1.1MB, not the stripped 941KB version).

**Verify:**
```bash
grep -a "snd_use_case_mgr_open" /usr/lib64/libasound.so.2  # Should return matches
ls -lh /usr/lib64/libasound.so.2.0.0  # Should be ~1.1MB
```

### Hardware Not Detected

**Symptom:** `/proc/asound/cards` is empty or shows wrong device.

**Solutions:**
1. Check USB connection: `lsusb | grep -i behringer`
2. Reload kernel module: `modprobe -r snd-usb-audio && modprobe snd-usb-audio`
3. Check `sound-*.txz` kernel version match: `uname -r`

### Kodis Start But No Audio

**Symptom:** Containers running, but no sound output.

**Debug Steps:**
1. Check sink assignments:
   ```bash
   export XDG_RUNTIME_DIR=/run/user/0
   export PULSE_SERVER=unix:$XDG_RUNTIME_DIR/pulse/native
   pactl list sink-inputs short  # Shows active streams
   ```
2. Verify Kodi environment variables: `docker inspect kodi-rot | grep -E "PULSE_SERVER|PULSE_SINK"`
3. Test sink manually:
   ```bash
   paplay --device=kodi_rot /usr/share/sounds/alsa/Front_Center.wav
   ```

### PA Exits Unexpectedly

**Symptom:** PA runs initially but exits after period of no audio activity.

**Cause:** Default `exit-idle-time=20` causes PA to exit after 20s of inactivity.

**Solution:** Set `exit-idle-time = -1` in `daemon.conf`.

## Lessons Learned

### 1. Avoid `/boot/config/go` for Complex Startup

**Problem:** Early boot timing issues, race conditions with hardware/services.

**Solution:** Use User Scripts Plugin with "At Startup of Array" event. This ensures Array is ready, services stable, hardware detected.

### 2. Declarative PA Configuration via `boot.pa`

**Problem:** `module-udev-detect` auto-loads `module-alsa-card`, causing hardware locks and conflicts.

**Solution:** Use `boot.pa` with explicit `load-module` directives. This gives deterministic module load order and avoids conflicts.

**Benefit:** No runtime `pactl` commands needed, cleaner architecture.

### 3. User Scripts Require Absolute Paths

**Problem:** User Scripts Plugin runs scripts from `/tmp/user.scripts/tmpScripts/`, causing relative path failures.

**Solution:** Always use absolute paths when calling scripts from User Script orchestrator:
```bash
# Wrong:
bash -x start_pulseaudio.sh

# Right:
bash -x /boot/config/plugins/pulseaudio/start_pulseaudio.sh
```

### 4. Staggered Kodi Start Essential

**Problem:** 5 Kodi containers starting simultaneously caused filesystem contention during playlist loading, resulting in slow/unreliable startup.

**Solution:** Staggered start with 5s delay between containers. Even with MariaDB library integration, playlists remain file-based and require staggering.

### 5. Package Persistence Critical

**Problem:** Installing packages to `/tmp/` for testing, then forgetting to copy to `/boot/extra/`, causes wrong versions to reinstall after reboot.

**Solution:** Always download packages directly to `/boot/extra/` before testing. Verify after reboot.

### 6. Kernel Version Matching

**Problem:** `sound-*.txz` package version mismatch with kernel causes module load failures.

**Solution:** Always check `uname -r` and download matching `sound-*.txz` from ich777 GitHub. Re-verify after Unraid updates.

## Performance Notes

- **Latency:** Sub-50ms total (PA processing + USB + network)
- **CPU Usage:** Negligible (<1% on modern CPUs)
- **Stability:** Rock-solid with declarative config, no crashes or audio dropouts
- **Scalability:** Tested with 5 simultaneous streams, easily expandable to 6 stereo pairs (12 channels)

## Future Enhancements

1. **MariaDB Integration:** Shared Kodi library across all rooms (database prepared, not yet activated)
2. **Dynamic Volume Control:** Web interface for per-room volume adjustment
3. **Stream Synchronization:** Ensure perfect audio sync across rooms (currently relies on local clocks)
4. **Fallback Handling:** Auto-recovery if PA crashes (watchdog script)

## Conclusion

This architecture provides a reliable, low-latency multi-room audio solution on Unraid. The key success factors were:
- Declarative PA configuration via `boot.pa`
- User Scripts Plugin for robust startup timing
- Staggered Kodi container startup
- Proper package management and persistence

The solution has been tested extensively and runs stable in production.

## References

- **PulseAudio Documentation:** https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/
- **ALSA Project:** https://alsa-project.org/
- **Unraid Forums:** https://forums.unraid.net/
- **ich777 Sound Drivers:** https://github.com/ich777/unraid-sound-driver

---

*Document Version 1.0 - 2025-11-24*
