# Reboot-Checkliste PulseAudio / UMC1820

Version: 2025-11-22

- Pakete prüfen (Größe/Version):
  - `ls -lh /boot/extra/alsa-lib-1.2.14-x86_64-1.txz` (≈1.1MB erwartet)
  - `ls -l /var/log/packages/alsa-lib* /var/log/packages/sound-*`
- Korrekte alsa-lib ersetzen (falls <1MB):
  - `cd /boot/extra && wget https://slackware.uk/slackware/slackware64-current/slackware64/l/alsa-lib-1.2.14-x86_64-1.txz`
- Nach Boot Symbol prüfen:
  - `grep -a "snd_use_case_mgr_open" /usr/lib64/libasound.so.2`
- PulseAudio neu starten (bei Bedarf):
  - `pulseaudio --kill && bash /boot/config/plugins/pulseaudio/start_pulseaudio.sh`
- Sinks prüfen (1 Master + 5 Remaps):
  - `pactl list sinks short`
- TCP-Modul prüfen (4713):
  - `pactl list modules short | grep tcp`
- Hardware/Module prüfen:
  - `cat /proc/asound/cards`
  - `lsmod | grep snd`
- Zeilenenden beachten (bei Deploy von Windows):
  - `sed -i 's/\r$//' /boot/config/plugins/pulseaudio/start_pulseaudio.sh`
