# Kodi Playlist Automation

Version: 1.0
Date: 2025-11-24

## Overview

Automated playlist management for 5 Kodi headless instances via JSON-RPC API.

**Phase 1 (Current):** Load predefined playlists at boot
**Phase 2 (Future):** Dynamic playlist optimization based on user feedback

## Architecture

### Current Setup

- 5 Kodi containers: kodi-rot/orange/gelb/gruen/blau
- IPs: 10.2.0.160-164
- JSON-RPC: Port 9090 (HTTP)
- Playlists: Stored in `/data/userdata/playlists/music/*.m3u` (container path)

**Genre Assignment:**
- kodi-rot (10.2.0.160): Rock
- kodi-orange (10.2.0.161): Trance / Progressive Psy
- kodi-gelb (10.2.0.162): Pop / Oldies
- kodi-gruen (10.2.0.163): Techno
- kodi-blau (10.2.0.164): Volksmusik

### Integration Point

**Script:** `start_kodi_after_audio.sh`
- Start Kodi container
- Wait for JSON-RPC readiness
- Load playlist via curl
- Continue to next container

## JSON-RPC Commands

### Player.Open (Direct Playlist File)

Load and play .m3u playlist:

```bash
curl -X POST http://10.2.0.160:9090/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "Player.Open",
    "params": {
      "item": {
        "file": "/data/userdata/playlists/music/Rock.m3u"
      }
    }
  }'
```

### Player.Open (Smart Playlist .xsp)

```bash
curl -X POST http://10.2.0.160:9090/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "Player.Open",
    "params": {
      "item": {
        "file": "special://profile/playlists/music/MySmartPlaylist.xsp"
      }
    }
  }'
```

### Playlist Manipulation Workflow

```bash
# Clear playlist (ID 0 = Audio)
curl -X POST http://10.2.0.160:9090/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"Playlist.Clear","params":{"playlistid":0},"id":1}'

# Add file to playlist
curl -X POST http://10.2.0.160:9090/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"Playlist.Add","params":{"playlistid":0,"item":{"file":"/media/music/song.mp3"}},"id":1}'

# Start playback
curl -X POST http://10.2.0.160:9090/jsonrpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"Player.Open","params":{"item":{"playlistid":0}}}'
```

**Playlist IDs:**
- 0: Audio
- 1: Video
- 2: Pictures

## Implementation

### start_kodi_after_audio.sh Integration

**Current (minimal):**
```bash
docker start kodi-rot || docker unpause kodi-rot
sleep 5
docker start kodi-orange || docker unpause kodi-orange
# ...
```

**Enhanced (with playlist loading):**
```bash
# Function: Start container and load playlist
start_kodi_with_playlist() {
  local color=$1
  local playlist=$2
  local ip=$3

  # Start container
  docker update --restart=no kodi-${color}
  docker start kodi-${color} || docker unpause kodi-${color}

  # Wait for JSON-RPC readiness (max 30s)
  for i in {1..30}; do
    if curl -s -X POST http://${ip}:9090/jsonrpc \
      -d '{"jsonrpc":"2.0","method":"JSONRPC.Ping","id":1}' \
      | grep -q "pong"; then
      break
    fi
    sleep 1
  done

  # Load playlist
  if [ -n "$playlist" ]; then
    curl -s -X POST http://${ip}:9090/jsonrpc \
      -H "Content-Type: application/json" \
      -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"Player.Open\",\"params\":{\"item\":{\"file\":\"${playlist}\"}}}"
  fi

  sleep 5
}

# Usage
start_kodi_with_playlist "rot" "/data/userdata/playlists/music/Rock.m3u" "10.2.0.160"
start_kodi_with_playlist "orange" "/data/userdata/playlists/music/Trance.m3u" "10.2.0.161"
start_kodi_with_playlist "gelb" "/data/userdata/playlists/music/Pop.m3u" "10.2.0.162"
start_kodi_with_playlist "gruen" "/data/userdata/playlists/music/Techno.m3u" "10.2.0.163"
start_kodi_with_playlist "blau" "/data/userdata/playlists/music/Volksmusik.m3u" "10.2.0.164"
```

### Configuration File (Optional)

`/boot/config/plugins/pulseaudio/kodi-playlists.conf`:
```bash
# Kodi Playlist Assignments
# Format: COLOR IP PLAYLIST_PATH
rot 10.2.0.160 /data/userdata/playlists/music/Rock.m3u
orange 10.2.0.161 /data/userdata/playlists/music/Trance.m3u
gelb 10.2.0.162 /data/userdata/playlists/music/Pop.m3u
gruen 10.2.0.163 /data/userdata/playlists/music/Techno.m3u
blau 10.2.0.164 /data/userdata/playlists/music/Volksmusik.m3u
```

## Readiness Check

**JSONRPC.Ping Method:**
```bash
curl -s -X POST http://10.2.0.160:9090/jsonrpc \
  -d '{"jsonrpc":"2.0","method":"JSONRPC.Ping","id":1}'

# Response if ready:
{"id":1,"jsonrpc":"2.0","result":"pong"}
```

## Error Handling

### JSON-RPC Not Ready
- Symptom: Connection refused or timeout
- Solution: Wait loop (up to 30s), then skip playlist loading

### Playlist File Not Found
- Symptom: Kodi ignores command silently
- Solution: Pre-check file existence via `docker exec`

### Container Not Started
- Symptom: No JSON-RPC response
- Solution: Log error, continue with next container (no blocking)

## Playlist Storage

**Container Path:** `/data/userdata/playlists/music/`
**Host Path:** `/mnt/user0/appdata/kodi-[color]/userdata/playlists/music/`

**Formats:**
- `.m3u`: Simple file list (relative paths to `/media/music/`)
- `.xsp`: Kodi Smart Playlist (XML, query-based)

**Example .m3u:**
```
#EXTM3U
/media/music/Artist/Album/01 - Track.flac
/media/music/Artist/Album/02 - Track.flac
```

**Example .xsp (Genre-based):**
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<smartplaylist type="songs">
  <name>Rock</name>
  <match>all</match>
  <rule field="genre" operator="is">
    <value>Rock</value>
  </rule>
  <order direction="ascending">random</order>
</smartplaylist>
```

## Phase 2: Dynamic Optimization (Future)

### Concept
- User feedback: Skip/Like/Dislike via JSON-RPC or Home Assistant
- Track ratings/skip counts in MariaDB
- Algorithm adjusts playlist weights
- Regenerate playlists periodically

### Required APIs
- `Player.GetItem` - Get currently playing track
- `AudioLibrary.SetSongDetails` - Update rating
- Custom DB tables for skip counts/preferences

### Integration Points
- Home Assistant dashboard for feedback buttons
- Audac R2 matrix integration (zone-specific preferences)
- Scheduled playlist regeneration (cron/User Script)

## Phase 3: Music Classification (Future)

### Concept
- Automated music analysis: Genre, mood, tempo, energy
- ML-based classification system
- Generate playlists based on classifications
- Requires separate classification project/pipeline

### Classification Dimensions
- Genre identification
- Mood analysis (happy, sad, energetic, calm)
- Tempo/BPM detection
- Energy level
- Vocal/Instrumental detection

### Integration
- Classification metadata → MariaDB
- Smart Playlists (.xsp) query classification tags
- Phase 2 feedback improves classification accuracy

## References

- [Kodi JSON-RPC API v12](https://kodi.wiki/view/JSON-RPC_API/v12)
- [Kodi JSON-RPC API v13](https://kodi.wiki/view/JSON-RPC_API/v13)
- [Smart Playlists](https://kodi.wiki/view/Smart_playlists)

## Testing

### Manual Playlist Load Test
```bash
# Check JSON-RPC availability
ssh root@10.0.0.44 'curl -s http://10.2.0.160:9090/jsonrpc \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"JSONRPC.Ping\",\"id\":1}"'

# Load test playlist
ssh root@10.0.0.44 'curl -s -X POST http://10.2.0.160:9090/jsonrpc \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"Player.Open\",\"params\":{\"item\":{\"file\":\"/data/userdata/playlists/music/test.m3u\"}}}"'

# Verify playback started
ssh root@10.0.0.44 'curl -s http://10.2.0.160:9090/jsonrpc \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"Player.GetActivePlayers\",\"id\":1}"'
```

## Next Steps

1. Create test playlists on each Kodi instance
2. Implement enhanced `start_kodi_after_audio.sh` with playlist loading
3. Test boot sequence with automatic playlist start
4. Document playlist file locations and naming conventions
5. Plan Phase 2 architecture for dynamic optimization
