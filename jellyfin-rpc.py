#!/bin/bash

# Copyright 2023 iiPython

# Modules
import atexit
import tomllib
from pathlib import Path
from getpass import getuser
from time import time, sleep

from requests import Session
from pypresence import Presence

# Initialization
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

session = Session()

# Ticks to seconds
def sec(n: int) -> float:
    return n / 10_000_000

# Create RPC
rpc = Presence(config.get("client_id", "1117545345690374277"))
rpc.connect()

print("\x1b[92m✓ Connected to discord!\x1b[0m")

atexit.register(rpc.clear)

# Start listening
cache_data, album_art_url, paused_tick = [None, None], None, 0
while True:
    sleep(float(config.get("update_time", 1)))

    # Fetch latest now playing data (multi-user support soon prob)
    user = session.get(f"{config['url']}/Sessions?api_key={config['api_key']}").json()[0]
    if "NowPlayingItem" not in user:
        paused_tick += 1
        if paused_tick == 4:
            paused_tick = 0
            rpc.clear()

        continue

    else:
        paused_tick = 0

    playing = user["NowPlayingItem"]
    track, album, artist = playing["Name"], playing["Album"], playing["AlbumArtist"]

    # Update RPC if track has changed
    new_cache_key = [playing["Id"], playing["AlbumId"]]
    if new_cache_key != cache_data[:2]:
        new_cache_key.append(time() + sec(playing["RunTimeTicks"]) - \
             sec(user["PlayState"]["PositionTicks"]))

        if new_cache_key[1] != cache_data[1]:
            def get_album_art() -> str:
                endpoint = config.get("url_public", config["url"])
                url = f"{endpoint}/Items/{playing['AlbumId']}/Images/Primary"
                return url if session.get(url).status_code == 200 else "noart"

            # Locate source of album art
            mb_album_id = playing["ProviderIds"].get("MusicBrainzAlbum")
            if mb_album_id is not None and config.get("musicbrainz_album_art") is True:
                album_art_url = f"https://coverartarchive.org/release/{mb_album_id}/front"
                if session.get(album_art_url).status_code != 200:
                    album_art_url = get_album_art()

            else:
                album_art_url = get_album_art()

            print("\x1b[94m🛈  Album changed and album art refreshed\x1b[0m")

        # Send change to RPC
        print(f"\x1b[94m🛈  {track} by {artist} on {album}\x1b[0m")
        rpc.update(
            state = f"{f'on {album} ' if album != track else ''} by {artist}",
            details = track,
            large_image = album_art_url,
            end = new_cache_key[2]
        )
        cache_data = new_cache_key

# CTRL+C or smth handler
rpc.clear()
