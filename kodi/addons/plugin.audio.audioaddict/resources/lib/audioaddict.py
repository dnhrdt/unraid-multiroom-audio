"""
AudioAddict API client.

Reverse-engineered from di-tui (Go) and verified against live endpoints.
Covers all 6 AudioAddict networks with a single API surface.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

# All AudioAddict networks share the same API structure
NETWORKS = {
    "di": {
        "name": "DI.FM",
        "listen_host": "listen.di.fm",
        "slug": "di",
    },
    "jazzradio": {
        "name": "JazzRadio",
        "listen_host": "listen.jazzradio.com",
        "slug": "jazzradio",
    },
    "radiotunes": {
        "name": "RadioTunes",
        "listen_host": "listen.radiotunes.com",
        "slug": "radiotunes",
    },
    "rockradio": {
        "name": "RockRadio",
        "listen_host": "listen.rockradio.com",
        "slug": "rockradio",
    },
    "classicalradio": {
        "name": "ClassicalRadio",
        "listen_host": "listen.classicalradio.com",
        "slug": "classicalradio",
    },
    "zenradio": {
        "name": "Zen Radio",
        "listen_host": "listen.zenradio.com",
        "slug": "zenradio",
    },
}

# Quality tiers: (path_segment, label, requires_premium)
QUALITY_TIERS = [
    ("public3", "Free (64 kbps AAC+)", False),
    ("premium_low", "Premium Low (40 kbps AAC+)", True),
    ("premium_medium", "Premium Medium (64 kbps AAC+)", True),
    ("premium", "Premium (128 kbps AAC+)", True),
    ("premium_high", "Premium High (320 kbps MP3)", True),
]

API_BASE = "https://api.audioaddict.com/v1"
TIMEOUT = 10


def _fetch_json(url):
    """Fetch a URL and return parsed JSON."""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_text(url):
    """Fetch a URL and return raw text."""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8")


def authenticate(network_slug, username, password):
    """
    Authenticate with username/password.

    Returns dict with 'listen_key' and 'api_key', or None on failure.
    """
    url = "{}/{}/members/authenticate".format(API_BASE, network_slug)
    data = urllib.parse.urlencode({
        "username": username,
        "password": password,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError:
        return None


def list_channels(listen_host, quality_tier):
    """
    Fetch channel list for a given quality tier.

    Returns list of dicts with keys: id, key, name, playlist.
    """
    url = "http://{}/{}".format(listen_host, quality_tier)
    return _fetch_json(url)


def list_channels_rich(network_slug):
    """
    Fetch rich channel metadata (descriptions, artwork, similar channels).

    Returns list of dicts with extended metadata.
    """
    url = "{}/{}/channels".format(API_BASE, network_slug)
    return _fetch_json(url)


def list_channel_filters(network_slug):
    """
    Fetch genre/category filters with associated channels.

    Returns list of dicts with keys: id, name, channels.
    """
    url = "{}/{}/channel_filters".format(API_BASE, network_slug)
    return _fetch_json(url)


def get_currently_playing(network_slug):
    """
    Fetch now-playing info for all channels.

    Returns list of dicts with keys: channel_id, channel_key, track.
    """
    url = "{}/{}/currently_playing".format(API_BASE, network_slug)
    try:
        return _fetch_json(url)
    except Exception:
        return []


def get_track_details(track_id):
    """
    Fetch track details including album art URL.

    Returns dict with keys: id, asset_url.
    """
    url = "{}/di/tracks/{}".format(API_BASE, track_id)
    try:
        return _fetch_json(url)
    except Exception:
        return None


def get_favorites_pls(listen_host, token):
    """
    Fetch user's favorites as PLS content.

    Returns raw PLS text, or None on failure.
    """
    url = "http://{}/premium_high/favorites.pls?{}".format(listen_host, token)
    try:
        return _fetch_text(url)
    except urllib.error.HTTPError:
        return None


def parse_pls(pls_text):
    """
    Parse a PLS playlist file.

    Returns list of (url, title) tuples.
    """
    entries = []
    files = {}
    titles = {}
    for line in pls_text.splitlines():
        line = line.strip()
        if line.lower().startswith("file"):
            key, _, value = line.partition("=")
            idx = key[4:]  # strip "File" prefix
            files[idx] = value
        elif line.lower().startswith("title"):
            key, _, value = line.partition("=")
            idx = key[5:]  # strip "Title" prefix
            titles[idx] = value
    for idx in sorted(files.keys(), key=lambda x: int(x)):
        entries.append((files[idx], titles.get(idx, "")))
    return entries


def resolve_stream_url(playlist_url, token=None):
    """
    Resolve a channel's playlist URL to an actual stream URL.

    Fetches the PLS file, parses it, returns the first stream URL
    with the token appended if provided.
    """
    pls_text = _fetch_text(playlist_url)
    entries = parse_pls(pls_text)
    if not entries:
        return None
    stream_url = entries[0][0]
    if token:
        stream_url = "{}?{}".format(stream_url, token)
    return stream_url


def build_channel_art_map(network_slug):
    """
    Build a dict mapping channel key to artwork URL.

    Uses the rich channel metadata endpoint.
    """
    art_map = {}
    try:
        channels = list_channels_rich(network_slug)
        for ch in channels:
            key = ch.get("key", "")
            images = ch.get("images", {})
            art_url = images.get("default", "")
            if art_url and art_url.startswith("//"):
                art_url = "https:" + art_url
            if key and art_url:
                art_map[key] = art_url
    except Exception:
        pass
    return art_map
