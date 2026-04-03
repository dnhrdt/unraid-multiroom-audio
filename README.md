# Kodi Multi-Room Audio on Unraid

A low-cost, software-defined multi-room audio system built entirely on Unraid. Up to 20 independent stereo streams from a single ~$400 mini server with a USB audio interface — no proprietary streaming hardware, no Snapcast, no expensive commercial PA systems.

## What This Is

Commercial multi-room audio solutions for hotels, restaurants, and clubs cost thousands. They require dedicated hardware per zone and proprietary management software. This project achieves the same result with:

- An **Unraid server** (any small x86 box with USB)
- A **Behringer UMC1820** (~$250, 12 channels) or similar USB audio interface
- **PulseAudio** for software-defined audio routing
- **Dockerized media players** (Kodi, but any audio player works)

The UMC1820 alone provides 5 stereo zones. Daisy-chain a second via ADAT for 10 zones. Use a UMC1820 + ADA8200 combo for up to 20 independent stereo streams — all from one USB connection.

## Why PulseAudio on Unraid Is Special

Nobody does this because it's not supposed to work. Unraid is Slackware-based with a non-persistent RAM filesystem. The shipped ALSA libraries are stripped. Kernel sound modules aren't included. Nothing survives a reboot unless you know exactly where to persist it.

This project solves all of that. It took significant trial and error — this repo is the working result.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Kodi Rot    │     │ Kodi Orange  │     │  Kodi Gelb   │  ...
│  10.2.0.160  │     │  10.2.0.161  │     │  10.2.0.162  │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │ TCP :4713          │                     │
       ▼                    ▼                     ▼
┌──────────────────────────────────────────────────────────┐
│                    PulseAudio (Host)                      │
│                                                          │
│  kodi_rot ──► Ch 0-1 ┐                                   │
│  kodi_orange ► Ch 2-3 ├──► umc1820_master (12ch)         │
│  kodi_gelb ──► Ch 4-5 │    S24LE @ 48kHz                 │
│  kodi_gruen ─► Ch 6-7 │                                  │
│  kodi_blau ──► Ch 8-9 ┘                                  │
└──────────────────────┬───────────────────────────────────┘
                       │ USB
                       ▼
              ┌─────────────────┐
              │ Behringer UMC1820│
              │ (12ch USB DAC)   │
              └────────┬────────┘
                       │ Analog (5 stereo pairs)
                       ▼
              ┌─────────────────┐
              │  Zone Amplifier  │
              │  (e.g. Audac R2) │
              └─────────────────┘
```

Each media player gets a dedicated stereo pair on the USB interface. PulseAudio remap sinks route each container's audio to the correct output channels. No mixing, no crosstalk — clean channel separation at 24-bit/48kHz.

## What You Can Do With This

- **Home multi-room audio**: Different music in every room, controlled independently from tablets/phones
- **Small venue / restaurant**: Background music per zone, managed via web interface or app
- **Office / coworking**: Independent audio zones without hardware per zone
- **Any audio player works**: This project uses Kodi, but MPD, VLC, Mopidy, or any PulseAudio-capable player can be substituted

## Key Components

| Component | Role | Cost |
|-----------|------|------|
| **Unraid Server** | Host OS, Docker runtime | ~$150 (mini PC) + license |
| **Behringer UMC1820** | 12-channel USB audio interface (5 stereo zones) | ~$250 |
| **PulseAudio 17.0** | Software audio routing — multichannel ALSA sink + remap sinks | Free |
| **Kodi Headless** | Media player containers (`fhriley/kodi-headless-novnc`) | Free |
| **Zone Amplifier** | Drives speakers per zone (e.g. Audac R2 matrix amp) | Varies |

**Total for 5-zone system: ~$400 + amplifier + speakers** (vs. $2,000-10,000+ for commercial solutions)

## The Hard Parts (and Solutions)

### PulseAudio on Unraid

Unraid ships with a stripped `alsa-lib` (941KB) missing UCM symbols. PulseAudio crashes on load:

```
undefined symbol: snd_use_case_mgr_open
```

**Fix:** Install the complete `alsa-lib` from Slackware Current in `/boot/extra/` (auto-installed at boot). Same for kernel sound modules — they must match `uname -r` exactly.

### Avoiding module-udev-detect

The default PulseAudio startup loads `module-udev-detect`, which auto-loads `module-alsa-card` and locks the sound device. With a multichannel setup, this creates conflicts.

**Fix:** Use a custom `boot.pa` that loads only what's needed — no default system.pa, no udev detection. Fully declarative.

### Boot Persistence

Unraid's rootfs lives in RAM. Everything in `/usr/`, `/etc/`, `/tmp/` is gone after reboot.

**Fix:**
- Packages → `/boot/extra/` (auto-installed)
- Scripts → `/boot/config/plugins/pulseaudio/`
- Startup → User Scripts Plugin ("At Startup of Array" event, not `/boot/config/go`)

### Docker Container Timing

Starting multiple containers simultaneously causes filesystem contention on shared mounts.

**Fix:** Staggered start with 5-second intervals. Containers use `restart: no` policy — the startup script manages lifecycle and ordering.

## File Structure

```
scripts/
  boot.pa                      # PulseAudio declarative config
  start_pulseaudio.sh           # PA startup + readiness check
  start_kodi_after_audio.sh     # Staggered Kodi container start
  kodi-stack-complete.yml       # Docker Compose reference
docs/
  pulseaudio-multiroom-architecture.md
  kodi-setup.md
  reboot-checklist.md
  unraid-ssh-setup.md
```

## Quick Start

### Prerequisites

- Unraid with a multichannel USB audio interface
- User Scripts plugin installed
- Docker with macvlan network configured

### 1. Install Packages

Download to `/boot/extra/` on the Unraid flash drive:

```bash
# Complete ALSA library (match your Slackware version)
wget -P /boot/extra/ https://slackware.uk/slackware/slackware64-current/slackware64/l/alsa-lib-1.2.14-x86_64-1.txz

# Kernel sound modules (MUST match uname -r)
wget -P /boot/extra/ https://github.com/ich777/unraid-sound-driver/releases/download/$(uname -r)/sound-*-$(uname -r)-1.txz
```

Install and verify:

```bash
installpkg /boot/extra/alsa-lib-*.txz /boot/extra/sound-*.txz
modprobe snd-usb-audio
cat /proc/asound/cards   # Should show your USB device
```

### 2. Deploy PulseAudio Config

```bash
mkdir -p /boot/config/plugins/pulseaudio
# Copy boot.pa, start_pulseaudio.sh, start_kodi_after_audio.sh
# Edit boot.pa to match your audio device and channel layout
```

### 3. Create User Script

In Unraid WebUI: Settings → User Scripts → Add New Script → paste orchestrator (see `docs/` for template). Set schedule to "At Startup of Array".

### 4. Build/Pull Kodi Image

The `kodi-pulse` image is based on `fhriley/kodi-headless-novnc:Omega` with PulseAudio client libraries added.

### 5. Configure and Start

Adapt `scripts/kodi-stack-complete.yml` to your network, deploy containers, reboot, and verify:

```bash
pactl list sinks short           # 6 sinks (1 master + 5 remap)
docker ps | grep kodi            # 5 containers, all healthy
curl -s http://<kodi-ip>:8080/jsonrpc -d '{"jsonrpc":"2.0","method":"JSONRPC.Version","id":1}'
```

## Remote Control

Each Kodi instance exposes:
- **HTTP/JSON-RPC** on port 8080 (Chorus2 web interface)
- **VNC** on port 5900 (noVNC for direct GUI access)
- **JSON-RPC TCP** on port 9090 (for remote apps)

Tested with [CODI Music Remote](https://kodimusicremote.com/) (iOS) — connect manually by IP, port 8080.

## Scaling

| USB Interface | Channels | Stereo Zones | Approx. Cost |
|---------------|----------|--------------|-------------|
| Behringer UMC404HD | 4 | 2 | ~$100 |
| Behringer UMC1820 | 12 | 5 (+ 2 reserved) | ~$250 |
| UMC1820 + ADAT expansion | 20 | 10 | ~$500 |
| UMC1820 + ADA8200 | 20 | 10 | ~$600 |

PulseAudio handles the routing in software. Add channels by expanding the `boot.pa` config with additional remap sinks.

## Network

All media player containers run on a dedicated VLAN (macvlan). PulseAudio accepts TCP connections from the VLAN subnet on port 4713. Containers reach the host PA server via the host's VLAN interface IP.

## Credits

- [fhriley/kodi-headless-novnc](https://github.com/fhriley/kodi-headless-novnc) — base Docker image
- [ich777/unraid-sound-driver](https://github.com/ich777/unraid-sound-driver) — kernel sound modules for Unraid
- The Unraid and Kodi communities

## License

MIT
