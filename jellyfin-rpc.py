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

# Start listening
def main() -> None:
    use_mb_art = config.get("musicbrainz_album_art") is True
    cache_data, album_art_url, paused_tick = [None, None], None, 0
    while True:
        sleep(float(config.get("update_time", 1)))

        # Fetch latest now playing data (multi-user support soon prob)
        user = session.get(
            f"{config['url']}/Sessions?api_key={config['api_key']}"
        ).json()[0]
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
                if mb_album_id is not None and use_mb_art:
                    album_art_url = f"https://coverartarchive.org/release/{mb_album_id}/front"
                    if session.get(album_art_url).status_code != 200:
                        album_art_url = get_album_art()

                else:
                    album_art_url = get_album_art()

                cprint("⟳ Album art cache was refreshed", "b")

            # Send change to RPC
            cprint(f"! {track} by {artist} on {album}", "b")
            rpc.update(
                state = f"{f'on {album} ' if album != track else ''} by {artist}",
                details = track,
                large_image = album_art_url,
                end = new_cache_key[2]
            )
            cache_data = new_cache_key

if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        onexit()
