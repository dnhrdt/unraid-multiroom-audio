# Unraid SSH Setup (Keys + Password)

Version: 2025-11-23

## Ziel

- Persistenter SSH-Zugriff per Key und per Passwort über Reboots.

## Schritte

1. SSH-Key erzeugen (ohne Passphrase)

- `ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_unraid -N ''`

1. Public Key auf den Server

- `type ~/.ssh/id_rsa_unraid.pub` (Windows) / `cat ~/.ssh/id_rsa_unraid.pub` (Linux/macOS)
- Auf dem Server (WebUI-Konsole):

```bash
mkdir -p /boot/config/ssh/root
echo "<DEIN_PUBKEY>" >> /boot/config/ssh/root/authorized_keys
chmod 700 /boot/config/ssh/root
chmod 600 /boot/config/ssh/root/authorized_keys
```

1. Symlink sicherstellen (zur Laufzeit und beim Boot)

- Laufzeit: `/root/.ssh -> /boot/config/ssh/root` (Unraid Standard)
- Boot (`/boot/config/go`):

```bash
ln -sfn /boot/config/ssh/root /root/.ssh
chmod 700 /boot/config/ssh/root
chmod 600 /boot/config/ssh/root/authorized_keys 2>/dev/null || true
```

1. Passwort-Login persistent halten

- Prefered: WebUI → Users → root → Passwort setzen
- Alternativ per Konsole:

```bash
passwd
cp /etc/shadow /boot/config/shadow
cp /etc/passwd /boot/config/passwd
sync
```

1. SSHD-Optionen verifizieren (Runtime)

```bash
sshd -T | egrep '^(passwordauthentication|usepam|permitrootlogin|pubkeyauthentication)'
```
Erwartet: `passwordauthentication yes`, `usepam yes`, `permitrootlogin yes`, `pubkeyauthentication yes`.

1. Tests
- Key: `ssh -i ~/.ssh/id_rsa_unraid root@<IP> 'echo ok'`
- Passwort: `ssh root@<IP>`
- Persistenztest: Reboot → beide Methoden erneut testen

## Hinweise
- WebUI bleibt die kanonische Quelle für SSH-Einstellungen; die hier gezeigten Schritte sind kompatibel.
- Rechte auf Flash-Verzeichnis sind wichtig (700/600), sonst verweigert SSH die Keys.
