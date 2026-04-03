"""
AudioAddict Radio — All-in-one Kodi plugin for the AudioAddict network.

Supports: DI.FM, JazzRadio, RadioTunes, RockRadio, ClassicalRadio, Zen Radio.
"""

import sys
import os
import urllib.parse

import xbmcgui
import xbmcplugin
import xbmcaddon

# Add resources/lib to path for our API module
ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo("path")
sys.path.insert(0, os.path.join(ADDON_PATH, "resources", "lib"))

import audioaddict  # noqa: E402

HANDLE = int(sys.argv[1])
BASE_URL = sys.argv[0]


def get_setting(key):
    return ADDON.getSetting(key)


def get_token():
    """Get the listen key from settings."""
    return get_setting("listen_key").strip()


def get_quality():
    """Get the selected quality tier path segment."""
    idx = int(get_setting("quality") or "0")
    return audioaddict.QUALITY_TIERS[idx][0]


def build_url(params):
    return "{}?{}".format(BASE_URL, urllib.parse.urlencode(params))


def show_networks():
    """Root menu: list all AudioAddict networks."""
    xbmcplugin.setContent(HANDLE, "files")
    for key, net in sorted(audioaddict.NETWORKS.items(), key=lambda x: x[1]["name"]):
        li = xbmcgui.ListItem(net["name"])
        li.setArt({"icon": "DefaultMusicCompilations.png"})
        url = build_url({"action": "network", "network": key})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)


def show_network_menu(network_key):
    """Network submenu: All Channels, By Genre, Favorites."""
    xbmcplugin.setContent(HANDLE, "files")

    # All Channels
    li = xbmcgui.ListItem("All Channels")
    url = build_url({"action": "channels", "network": network_key})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

    # By Genre
    li = xbmcgui.ListItem("By Genre")
    url = build_url({"action": "filters", "network": network_key})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

    # Favorites (only if token is set)
    token = get_token()
    if token:
        li = xbmcgui.ListItem("Favorites")
        li.setArt({"icon": "DefaultMusicPlaylists.png"})
        url = build_url({"action": "favorites", "network": network_key})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)

    xbmcplugin.endOfDirectory(HANDLE)


def show_channels(network_key):
    """List all channels for a network."""
    net = audioaddict.NETWORKS[network_key]
    quality = get_quality()

    channels = audioaddict.list_channels(net["listen_host"], quality)
    if not channels:
        xbmcgui.Dialog().notification("AudioAddict", "Could not load channels", xbmcgui.NOTIFICATION_ERROR)
        return

    art_map = audioaddict.build_channel_art_map(net["slug"])
    now_playing = _build_now_playing_map(net["slug"])

    xbmcplugin.setContent(HANDLE, "songs")
    for ch in sorted(channels, key=lambda c: c.get("name", "")):
        _add_channel_item(ch, net, art_map, now_playing)
    xbmcplugin.endOfDirectory(HANDLE)


def show_filters(network_key):
    """List genre filters for a network."""
    filters = audioaddict.list_channel_filters(network_key)
    if not filters:
        xbmcgui.Dialog().notification("AudioAddict", "Could not load genres", xbmcgui.NOTIFICATION_ERROR)
        return

    xbmcplugin.setContent(HANDLE, "files")
    for f in filters:
        name = f.get("name", "Unknown")
        channels = f.get("channels", [])
        if not channels:
            continue
        li = xbmcgui.ListItem("{} ({})".format(name, len(channels)))
        li.setArt({"icon": "DefaultMusicGenre.png"})
        url = build_url({"action": "filter_channels", "network": network_key, "filter_id": f["id"]})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=True)
    xbmcplugin.endOfDirectory(HANDLE)


def show_filter_channels(network_key, filter_id):
    """List channels within a specific genre filter."""
    net = audioaddict.NETWORKS[network_key]
    quality = get_quality()
    filter_id = int(filter_id)

    # Get filter data for channel keys in this genre
    filters = audioaddict.list_channel_filters(network_key)
    filter_channel_keys = set()
    for f in filters:
        if f.get("id") == filter_id:
            for ch in f.get("channels", []):
                filter_channel_keys.add(ch.get("key", ""))
            break

    # Get playable channel list with playlist URLs
    channels = audioaddict.list_channels(net["listen_host"], quality)
    if not channels:
        return

    art_map = audioaddict.build_channel_art_map(net["slug"])
    now_playing = _build_now_playing_map(net["slug"])

    xbmcplugin.setContent(HANDLE, "songs")
    for ch in sorted(channels, key=lambda c: c.get("name", "")):
        if ch.get("key", "") in filter_channel_keys:
            _add_channel_item(ch, net, art_map, now_playing)
    xbmcplugin.endOfDirectory(HANDLE)


def show_favorites(network_key):
    """List user's favorite channels."""
    net = audioaddict.NETWORKS[network_key]
    token = get_token()
    if not token:
        xbmcgui.Dialog().notification("AudioAddict", "Listen key required for favorites", xbmcgui.NOTIFICATION_WARNING)
        return

    pls_text = audioaddict.get_favorites_pls(net["listen_host"], token)
    if not pls_text:
        xbmcgui.Dialog().notification("AudioAddict", "Could not load favorites", xbmcgui.NOTIFICATION_ERROR)
        return

    entries = audioaddict.parse_pls(pls_text)
    # Strip network name prefix from titles
    prefix = "{} - ".format(net["name"].upper())

    art_map = audioaddict.build_channel_art_map(net["slug"])

    xbmcplugin.setContent(HANDLE, "songs")
    for playlist_url, title in entries:
        name = title.replace(prefix, "", 1) if title.startswith(prefix) else title
        li = xbmcgui.ListItem(name)
        li.setProperty("IsPlayable", "true")
        li.setInfo("music", {"title": name})
        # Try to find artwork by matching name to channel key
        for key, art_url in art_map.items():
            if key.replace("-", " ").replace("_", " ").lower() == name.lower():
                li.setArt({"thumb": art_url, "icon": art_url})
                break
        url = build_url({"action": "play_pls", "pls_url": playlist_url})
        xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)
    xbmcplugin.endOfDirectory(HANDLE)


def play_channel(playlist_url):
    """Resolve a channel's PLS URL and start playback."""
    token = get_token()
    stream_url = audioaddict.resolve_stream_url(playlist_url, token if token else None)
    if not stream_url:
        xbmcgui.Dialog().notification("AudioAddict", "Could not resolve stream", xbmcgui.NOTIFICATION_ERROR)
        return
    li = xbmcgui.ListItem(path=stream_url)
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def play_pls(pls_url):
    """Resolve a favorites entry URL. May be a .pls file or a direct stream URL."""
    token = get_token()
    if ".pls" in pls_url.split("?")[0]:
        # It's a PLS file — resolve to actual stream URL
        stream_url = audioaddict.resolve_stream_url(pls_url, token if token else None)
    else:
        # It's already a direct stream URL (favorites often return these)
        stream_url = pls_url
    if not stream_url:
        xbmcgui.Dialog().notification("AudioAddict", "Could not resolve stream", xbmcgui.NOTIFICATION_ERROR)
        return
    li = xbmcgui.ListItem(path=stream_url)
    xbmcplugin.setResolvedUrl(HANDLE, True, li)


def login():
    """Authenticate with username/password and save listen key."""
    username = get_setting("username").strip()
    password = get_setting("password").strip()
    if not username or not password:
        xbmcgui.Dialog().notification("AudioAddict", "Enter username and password in settings", xbmcgui.NOTIFICATION_WARNING)
        return
    result = audioaddict.authenticate("di", username, password)
    if result and result.get("listen_key"):
        ADDON.setSetting("listen_key", result["listen_key"])
        xbmcgui.Dialog().notification("AudioAddict", "Login successful!", xbmcgui.NOTIFICATION_INFO)
    else:
        xbmcgui.Dialog().notification("AudioAddict", "Login failed", xbmcgui.NOTIFICATION_ERROR)


def _build_now_playing_map(network_slug):
    """Build dict mapping channel_id to track info."""
    now_playing = {}
    for cp in audioaddict.get_currently_playing(network_slug):
        now_playing[cp.get("channel_id")] = cp.get("track", {})
    return now_playing


def _add_channel_item(ch, net, art_map, now_playing):
    """Add a playable channel ListItem to the directory."""
    name = ch.get("name", "Unknown")
    key = ch.get("key", "")
    channel_id = ch.get("id")

    # Build label with now-playing info
    label = name
    track = now_playing.get(channel_id, {})
    artist = track.get("display_artist", "")
    title = track.get("display_title", "")
    if artist and title:
        label = "{} — {} - {}".format(name, artist, title)

    li = xbmcgui.ListItem(label)
    li.setProperty("IsPlayable", "true")

    info = {"title": name}
    if artist:
        info["artist"] = artist
    if title:
        info["title"] = title
    li.setInfo("music", info)

    # Artwork
    art_url = art_map.get(key, "")
    if art_url:
        li.setArt({"thumb": art_url, "icon": art_url, "fanart": art_url})

    url = build_url({"action": "play", "playlist_url": ch.get("playlist", "")})
    xbmcplugin.addDirectoryItem(HANDLE, url, li, isFolder=False)


def router():
    """Route plugin calls based on URL parameters."""
    params = dict(urllib.parse.parse_qsl(sys.argv[2].lstrip("?")))
    action = params.get("action", "")

    if not action:
        show_networks()
    elif action == "network":
        show_network_menu(params["network"])
    elif action == "channels":
        show_channels(params["network"])
    elif action == "filters":
        show_filters(params["network"])
    elif action == "filter_channels":
        show_filter_channels(params["network"], params["filter_id"])
    elif action == "favorites":
        show_favorites(params["network"])
    elif action == "play":
        play_channel(params["playlist_url"])
    elif action == "play_pls":
        play_pls(params["pls_url"])
    elif action == "login":
        login()


if __name__ == "__main__":
    router()
