# Kodi-Headless Setup auf Star Destroyer - Zusammenfassung

## Netzwerk-Setup ✅
- **VLAN 2 (Media-VLAN)** in Unraid aktiviert: Interface `eth0.2` mit Subnet 10.2.0.0/24
- Docker-Netzwerk nutzt macvlan auf eth0.2
- 5 Kodi-Instanzen mit festen IPs:
  - kodi-rot: 10.2.0.160
  - kodi-orange: 10.2.0.161
  - kodi-gelb: 10.2.0.162
  - kodi-gruen: 10.2.0.163
  - kodi-blau: 10.2.0.164
- Firewall-Regel: VLAN 2 → Star Destroyer (10.0.0.44:3306) für DB-Zugriff

## Container-Setup ✅
- Image: `fhriley/kodi-headless-novnc:Omega`
- Portainer Stack deployed mit statischen IPs
- Volumes: 
  - `/mnt/user0/appdata/kodi-[farbe]:/data`
  - `/mnt/user0/Audio:/media/music:ro`
- Ports pro Container:
  - 8000: noVNC (GUI im Browser)
  - 8080: Kodi Webinterface
  - 9090: JSON-RPC

## Docker Stack (Portainer)
```yaml
version: "3"
services:
  kodi-rot:
    image: fhriley/kodi-headless-novnc:Omega
    container_name: kodi-rot
    init: true
    networks:
      eth02:
        ipv4_address: 10.2.0.160
    environment:
      - KODI_DB_HOST=10.0.0.44
      - KODI_DB_USER=kodi
      - KODI_DB_PASS=[passwort]
      - KODI_UID=99
      - KODI_GID=100
      - TZ=Europe/Berlin
    volumes:
      - /mnt/user0/appdata/kodi-rot:/data
      - /mnt/user0/Audio:/media/music:ro
    restart: unless-stopped

  kodi-orange:
    image: fhriley/kodi-headless-novnc:Omega
    container_name: kodi-orange
    init: true
    networks:
      eth02:
        ipv4_address: 10.2.0.161
    environment:
      - KODI_DB_HOST=10.0.0.44
      - KODI_DB_USER=kodi
      - KODI_DB_PASS=[passwort]
      - KODI_UID=99
      - KODI_GID=100
      - TZ=Europe/Berlin
    volumes:
      - /mnt/user0/appdata/kodi-orange:/data
      - /mnt/user0/Audio:/media/music:ro
    restart: unless-stopped

  kodi-gelb:
    image: fhriley/kodi-headless-novnc:Omega
    container_name: kodi-gelb
    init: true
    networks:
      eth02:
        ipv4_address: 10.2.0.162
    environment:
      - KODI_DB_HOST=10.0.0.44
      - KODI_DB_USER=kodi
      - KODI_DB_PASS=[passwort]
      - KODI_UID=99
      - KODI_GID=100
      - TZ=Europe/Berlin
    volumes:
      - /mnt/user0/appdata/kodi-gelb:/data
      - /mnt/user0/Audio:/media/music:ro
    restart: unless-stopped

  kodi-gruen:
    image: fhriley/kodi-headless-novnc:Omega
    container_name: kodi-gruen
    init: true
    networks:
      eth02:
        ipv4_address: 10.2.0.163
    environment:
      - KODI_DB_HOST=10.0.0.44
      - KODI_DB_USER=kodi
      - KODI_DB_PASS=[passwort]
      - KODI_UID=99
      - KODI_GID=100
      - TZ=Europe/Berlin
    volumes:
      - /mnt/user0/appdata/kodi-gruen:/data
      - /mnt/user0/Audio:/media/music:ro
    restart: unless-stopped

  kodi-blau:
    image: fhriley/kodi-headless-novnc:Omega
    container_name: kodi-blau
    init: true
    networks:
      eth02:
        ipv4_address: 10.2.0.164
    environment:
      - KODI_DB_HOST=10.0.0.44
      - KODI_DB_USER=kodi
      - KODI_DB_PASS=[passwort]
      - KODI_UID=99
      - KODI_GID=100
      - TZ=Europe/Berlin
    volumes:
      - /mnt/user0/appdata/kodi-blau:/data
      - /mnt/user0/Audio:/media/music:ro
    restart: unless-stopped

networks:
  eth02:
    name: eth0.2
    external: true
```

## MariaDB ✅
- **Status:** Bereits installiert und konfiguriert
- Über Unraid Community Apps (LinuxServer.io Image)
- Läuft auf Star Destroyer (10.0.0.44:3306)
- Datenbank-Name: `kodi`
- User: `kodi` mit Passwort

## Nächste Schritte

### 1. Kodi Initial-Setup (pro Container)
- Browser öffnen: `http://10.2.0.[160-164]:8000` für noVNC GUI
- Musik-Source hinzufügen: `/media/music`
- Library-Scan starten
- Add-ons installieren nach Bedarf

### 2. Datenbank-Verbindung prüfen
Die DB-Verbindung wird automatisch über die Docker ENV-Variablen konfiguriert. 
Check in jedem Container unter `/data/userdata/advancedsettings.xml`:
```xml
<advancedsettings>
  <musicdatabase>
    <type>mysql</type>
    <host>10.0.0.44</host>
    <port>3306</port>
    <user>kodi</user>
    <pass>[passwort]</pass>
    <name>kodi</name>
  </musicdatabase>
</advancedsettings>
```

### 3. Gemeinsame Library
- Erster Kodi (z.B. kodi-rot) scannt die komplette Musik-Library
- Andere Kodis sehen sofort die gleiche Library (gemeinsame DB)
- Wiedergabe-Status wird zwischen allen Instanzen synchronisiert

### 4. Remote Control
- Kodi Remote Apps können sich via JSON-RPC auf Port 9090 verbinden
- Web-Interface auf Port 8080
- Home Assistant Integration möglich

## Wichtige Pfade
- Kodi-Configs: `/mnt/user0/appdata/kodi-[farbe]/userdata/`
- Musik-Daten: `/mnt/user0/Audio` (direkt gemountet, keine sources.xml nötig)
- DB-Verbindung: Automatisch über Docker ENV-Variablen

## Besonderheiten
- Alle 5 Kodis teilen sich eine gemeinsame Musik-Datenbank
- Direkter Volume-Mount der Audio-Dateien (kein SMB/NFS)
- `/mnt/user0` statt `/mnt/user` (kein Cache-Drive vorhanden)
- VLAN-Isolation mit gezielter Firewall-Regel für DB-Zugriff

## Troubleshooting

### Container startet nicht
```bash
docker logs kodi-[farbe]
```

### Datenbank-Verbindung prüfen
```bash
docker exec -it mariadb-kodi mysql -u kodi -p
SHOW DATABASES;
USE kodi;
SHOW TABLES;
```

### Netzwerk-Diagnose
```bash
docker exec -it kodi-[farbe] ping 10.0.0.44
docker exec -it kodi-[farbe] nc -zv 10.0.0.44 3306
```

### SSH-Zugriff auf Star Destroyer
Falls SSH nicht läuft:
```bash
/etc/rc.d/rc.sshd restart
```

## Backup-Strategie
- Kodi-Configs: `/mnt/user0/appdata/kodi-*` regelmäßig sichern
- MariaDB: Automated Backups via LinuxServer.io Container
- Audio-Daten: Auf Array mit Parity bereits geschützt