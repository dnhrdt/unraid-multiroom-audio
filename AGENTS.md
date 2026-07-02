# Repository Instructions

Conversation with Michael: German, informal "du".
Code, comments, commits, and persistent docs: English unless Michael asks otherwise.

## System Criticality

This repo operates a production Unraid multi-room audio system. Treat Unraid
("Star Destroyer") as a 24/7 customer production system, not as a lab machine.

The PulseAudio/ALSA/UMC1820 stack is known fragile. It took substantial work to
make it reliable, and kernel or package changes can break audio in non-obvious
ways.

## Unraid SSH Access

Use the dedicated Unraid SSH key for Star Destroyer:

```bash
ssh -i ~/.ssh/id_rsa_unraid -o BatchMode=yes root@10.0.0.44 '<command>'
```

Do not use the Fleet/KeeAgent key for Unraid access. That key is not authorized
on Star Destroyer and will fail even when KeeAgent is working correctly.

## Unraid Change Policy

Read-only diagnostics are allowed.

Before making any write/change on Unraid, including but not limited to package
install/removal, editing `/boot`, restarting services, restarting containers,
loading/unloading kernel modules, USB reset/rebind, or changing mixer state:

1. Identify the exact current state that will be touched.
2. Back up that state first, on Unraid or in the repo as appropriate.
3. Define the exact rollback command or restore procedure before changing it.
4. State the planned change and rollback path to Michael.
5. Proceed only when the change is necessary and the rollback is credible.

Do not "just install" packages, reinstall libraries, restart PulseAudio, restart
Kodi containers, reload `snd-usb-audio`, or rewrite files on `/boot` as a quick
diagnostic shortcut. If a change is needed for diagnosis, treat it as a
production change and follow the policy above.

If a live Unraid state may differ from the repo, preserve the live state before
deploying repo files over it. Never assume the repo is the live source of truth
unless verified.

## Backup Before Unraid Changes

Before any Unraid write/change, create a recovery point appropriate to the
change scope.

For broad or uncertain changes, prefer a native Unraid boot-device backup first:

- WebGUI: Main -> Boot Device -> Boot Device Backup.
- If Unraid Connect flash backup is enabled, verify a recent flash backup
  exists and understand that it is configuration-focused, not a full runtime
  system snapshot.

For audio-stack work, also capture a repo-local, timestamped evidence snapshot
before changing anything. Include at minimum:

- `/boot/config/plugins/pulseaudio/`
- `/boot/config/plugins/user.scripts/scripts/pulseaudio_for_kodi/script`
- `/boot/extra/*alsa*`
- `/boot/extra/*sound*`
- `ls -l` and hashes for the files above
- `/var/log/packages/alsa-lib*`
- `/var/log/packages/sound-*`
- current `uname -r`, `/proc/asound/cards`, `pactl` sink/client/input state,
  ALSA mixer state, relevant `/proc/asound/card*/pcm*/sub*/status` and
  `hw_params`, Docker status/env for `kodi-*`, and recent audio logs

The snapshot must be stored under a repo-owned topic directory, not in bare
temporary storage. Do not rely on Unraid runtime files under `/usr`, `/etc`, or
`/var` as persistent rollback sources unless they were explicitly captured.

## Recovery Discipline

When investigating audio failures:

- Prefer evidence from logs, `/proc`, `/sys`, `pactl`, `aplay`, `amixer`,
  Docker inspect, and Kodi JSON-RPC before changing runtime state.
- Separate observation from intervention in the notes.
- Record every production change made during the session, including timestamps
  and touched paths.
- If a change is later reverted, verify byte-level or command-level equivalence
  where practical.

## Known Production Paths

- PulseAudio config: `/boot/config/plugins/pulseaudio/`
- User Scripts orchestrator:
  `/boot/config/plugins/user.scripts/scripts/pulseaudio_for_kodi/script`
- Persistent packages: `/boot/extra/`
- Kodi appdata: `/mnt/user0/appdata/kodi-*`
