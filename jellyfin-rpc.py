#!/bin/env python3

# Copyright 2023 iiPython

# Modules
import atexit
import tomllib
from pathlib import Path
from getpass import getuser
from time import time, sleep
from base64 import b64encode
from datetime import datetime, timedelta

from requests import Session
from pypresence import Presence, PipeClosed

# Load configuration
config = None
for location in [
    f"/home/{getuser()}/.config/iipython/jellyfin-rpc.toml",
    "/etc/jellyfin-rpc.toml"
]:
    location = Path(location)
    if location.is_file():
        try:
            with open(location, "r") as fh:
                config = tomllib.loads(fh.read())

        except tomllib.TOMLDecodeError:
            exit(f"error: invalid toml found in {location}")

        except PermissionError:
            pass  # What else would error? Pretty sure just perms

if config is None:
    exit("error: no valid configuration file found")

# Initialization
colors = {"r": 31, "g": 32, "b": 34}

def sec(n: int) -> float:
    return n / 10_000_000  # Ticks to seconds

def cprint(message: str, color: str) -> None:
    print(f"\x1b[{colors[color]}m{message}\x1b[0m")

session = Session()
rpc = Presence(config.get("client_id", "1117545345690374277"))
rpc.connect()

cprint("✓ Connected to discord!", "g")

# Ensure RPC is cleared at exit
def onexit() -> None:
    rpc.clear()
    cprint("✓ Disconnected from discord!", "r")

atexit.register(rpc.clear)

# Configuration
USE_MB = config.get("musicbrainz_album_art") is True
USE_IMGPROXY = config.get("imageproxy_enabled") is True
IMGPROXY_URL = config.get("imageproxy_url", "https://images.iipython.dev")
PUB_ENDPOINT = config.get("url_public", config["url"])
UPDATE_TIME = float(config.get("update_time", 1))
TICK_SENS = UPDATE_TIME + float(config.get("tick_sensitivity", 2))

# Start listening
class Cache(object):
    def __init__(self) -> None:
        self.last_item = (0, None)
        self.last_track = None
        self.last_tick = 0

def update(cache: Cache) -> None:

    # Load user information
    user_session = session.get(
        f"{config['url']}/Sessions?api_key={config['api_key']}"
    ).json()[0]
    state, item = user_session["PlayState"], user_session.get("NowPlayingItem")

    # Handle clearing RPC
    if (item is None) or (
        (
            datetime.strptime(
                user_session["LastPlaybackCheckIn"].split(".")[0],
                "%Y-%m-%dT%H:%M:%S"
            ) < (datetime.utcnow() - timedelta(seconds = 11))
        ) and not state["IsPaused"]
    ):
        if ((time() - cache.last_item[0]) > 5) and not cache.last_item[1]:
            rpc.clear()
            cprint("! Nothing is actively playing", "b")
            cache.last_item = (time(), True)

        return

    else:
        cache.last_item = (time(), False)

    # Check tick status
    tick = sec(state["PositionTicks"])
    tick_changed = (tick > (cache.last_tick + TICK_SENS)) or \
                    (tick < (cache.last_tick - TICK_SENS))

    # Handle updating status
    track, album, artist, paused = (
        item["Name"],
        item["Album"],
        item["AlbumArtist"],
        "paused" if state["IsPaused"] else "playing"
    )
    cache_changed = (cache.last_track != (item["Id"], paused))
    if cache_changed or tick_changed:

        # Fetch album art
        art_uri = f"{PUB_ENDPOINT}/Items/{item['AlbumId']}/Images/Primary"
        if USE_MB:
            mbid = item["ProviderIds"].get("MusicBrainzAlbum")
            if mbid is not None:
                art_uri = f"https://coverartarchive.org/release/{mbid}/front"

        elif USE_IMGPROXY and (IMGPROXY_URL is not None):
            art_uri = f"{IMGPROXY_URL}/sig/{b64encode(art_uri.encode()).decode()}.jpg"

        # Update RPC
        track_status = paused if cache_changed else "position update"
        cprint(f"! {track} by {artist} on {album} ({track_status})", "b")
        rpc.update(
            state = f"{f'on {album} ' if album != track else ''} by {artist}",
            details = track,
            large_image = art_uri,
            large_text = album if len(album) >= 2 else f"Album: {album}",
            small_image = paused,
            small_text = paused.capitalize(),
            end = (
                time() + sec(item["RunTimeTicks"]) - tick
                if not state["IsPaused"] else None
            )
        )
        cache.last_track = (item["Id"], paused)

    cache.last_tick = tick

def main() -> None:
    cache = Cache()
    while True:
        sleep(UPDATE_TIME)
        try:
            update(cache)

        except PipeClosed:
            rpc.connect()

if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        onexit()
