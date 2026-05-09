# Reboot and Unraid Update Checklist

Version: 2026-05-09

## When Unraid Is Updated

The `sound-*.txz` package is kernel-specific. After every Unraid update, verify
that the installed kernel and the persistent sound package match exactly.

```bash
uname -r
ls -lh /boot/extra/sound-*.txz /boot/extra/alsa-lib-*.txz
```

Example known-good state for Unraid 7.2.5:

```text
Kernel: 6.12.85-Unraid
Sound package: /boot/extra/sound-20260430-6.12.85-Unraid-1.txz
ALSA library: /boot/extra/alsa-lib-1.2.14-x86_64-1.txz
```

If `uname -r` does not match the `sound-*` package name, download the matching
release from:

```text
https://github.com/ich777/unraid-sound-driver/releases
```

For the ALSA library, keep the known-good 1.2.14 package:

```text
https://slackware.uk/cumulative/slackware64-current/slackware64/l/alsa-lib-1.2.14-x86_64-1.txz
```

Do not replace this with Slackware-current `alsa-lib-1.2.15.3` unless retested.
It was tested on 2026-05-09 and broke PulseAudio with:

```text
undefined symbol: snd_use_case_mgr_open
```

## Expected Runtime State

Hardware and kernel module:

```bash
cat /proc/asound/cards
lsmod | grep '^snd'
```

Expected card:

```text
0 [UMC1820]: USB-Audio - UMC1820
```

PulseAudio:

```bash
export PULSE_SERVER=127.0.0.1:4713
pactl list sinks short
pactl get-sink-volume umc1820_master
ss -tlnp | grep 4713
```

Expected sinks:

```text
umc1820_master
kodi_rot
kodi_orange
kodi_gelb
kodi_gruen
kodi_blau
```

Expected master volume:

```text
63% / -12.04 dB
```

Kodi containers:

```bash
docker ps --format '{{.Names}} {{.Status}}' | grep -E '^kodi-'
```

Expected: all five containers healthy.

## Recovery Sequence

Use this sequence after a kernel update or if Kodi playback runs through tracks
too quickly while files are still readable.

```bash
upgradepkg --install-new /boot/extra/alsa-lib-1.2.14-x86_64-1.txz
installpkg /boot/extra/sound-*-$(uname -r)-1.txz
depmod -a "$(uname -r)"
modprobe snd-usb-audio
cat /proc/asound/cards
```

If the UMC1820 is visible, restart PulseAudio:

```bash
kill $(pidof pulseaudio) 2>/dev/null || true
sleep 2
bash /boot/config/plugins/pulseaudio/start_pulseaudio.sh
export PULSE_SERVER=127.0.0.1:4713
pactl list sinks short
```

Then restart Kodi containers staggered:

```bash
for color in rot orange gelb gruen blau; do
  docker restart kodi-$color
  sleep 5
done
```

## Notes

- Runtime rootfs changes on Unraid are ephemeral; persistent packages must live in `/boot/extra/`.
- Keep old packages in a dated backup directory before replacing them.
- If `cat /proc/asound/cards` is missing entirely but `lsusb` shows the UMC1820, suspect a missing or mismatched sound driver package.
- If PulseAudio has no sinks, check `/var/log/syslog` for `module-alsa-sink` errors.
- When deploying scripts from Windows, normalize line endings:

```bash
sed -i 's/\r$//' /boot/config/plugins/pulseaudio/start_pulseaudio.sh
```
