#!/usr/bin/env python3
# Copyright 2023 iiPython

# Modules
import atexit
import tomllib
from pathlib import Path
from getpass import getuser
from time import time, sleep
from base64 import urlsafe_b64encode

from pydbus import SessionBus
from gi.repository.GLib import GError
from pypresence import Presence, PipeClosed, DiscordNotFound

# Initialization
mp2 = "org.mpris.MediaPlayer2"

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

UPDATE_TIME = float(config.get("update_time", 1))
TICK_SENS = UPDATE_TIME + float(config.get("tick_sensitivity", 2))
USE_IMGPROXY = config.get("imageproxy_enabled") is True
IMGPROXY_URL = config.get("imageproxy_url", "https://images.iipython.dev")
PUB_ENDPOINT = config.get("url_public", config["url"])

# Colored logging
colors = {"r": 31, "g": 32, "b": 34}
def cprint(message: str, color: str) -> None:
    print(f"\x1b[{colors[color]}m{message}\x1b[0m")

# Handle RPC
while True:
    try:
        rpc = Presence(config.get("client_id", "1117545345690374277"))
        rpc.connect()
        break

    except DiscordNotFound:
        sleep(UPDATE_TIME)

cprint("✓ Connected to discord!", "g")

# Ensure RPC is cleared at exit
def onexit() -> None:
    rpc.clear()
    cprint("✓ Disconnected from discord!", "r")

atexit.register(rpc.clear)

# Handle Feishin
class FeishinMPRISReader(object):
    def __init__(self) -> None:
        self.bus = SessionBus()
        self.connect()

    def connect(self) -> None:
        self.last, self.position = None, 0
        while True:
            try:
                self.feishin = self.bus.get(mp2 + ".Feishin", "/org/mpris/MediaPlayer2")
                cprint("✓ Connected to MPRIS!", "g")
                break

            except GError:
                sleep(1)

    def get_current(self) -> dict:
        try:
            md = self.feishin.Metadata
            return {
                "art": md.get("mpris:artUrl"),
                "name": md.get("xesam:title"),
                "album": md.get("xesam:album"),
                "artist": md.get("xesam:artist", [None])[0],
                "status": self.feishin.PlaybackStatus,

                # Microsecond attributes
                "length": md.get("mpris:length", 0) / 1000000,
                "position": self.feishin.Position / 1000000
            }

        except GError:
            cprint("! Feishin has been closed.", "b")
            rpc.clear()
            self.connect()
            return self.get_current()

feishin = FeishinMPRISReader()

# Updating
def update() -> None:

    # Fetch current track info
    info = feishin.get_current()
    cache_key = (info["name"], info["album"], info["artist"], info["status"])
    tick_changed = (info["position"] > (feishin.position + TICK_SENS)) or \
                        (info["position"] < (feishin.position - TICK_SENS))

    # Handle updating
    cache_changed = cache_key != feishin.last
    if (cache_changed or tick_changed) and info["name"] is not None:
        track, album, artist, status = info["name"], info["album"], info["artist"], info["status"]
        if (status == "Paused") and not info["position"]:
            feishin.last = cache_key
            return rpc.clear()

        # Handle cover art
        art_uri = info["art"].replace(config["url"], PUB_ENDPOINT).replace("&v=1.13.0&c=feishin&size=300", "&v=1&c=a")
        if USE_IMGPROXY and IMGPROXY_URL.strip():
            art_uri = f"{IMGPROXY_URL}/0/{urlsafe_b64encode(art_uri.encode()).rstrip(b'=').decode()}.jpg"

        # Update RPC
        track_status = status if cache_changed else "position update"
        cprint(f"! {track} by {artist} on {album} ({track_status})", "b")
        rpc.update(
            name = artist,
            state = f"on {album}",
            details = track,
            large_image = art_uri,
            large_text = album,
            small_image = status.lower(),
            small_text = status,
            end = (
                time() + info["length"] - info["position"]
                if status == "Playing" else None
            )
        )
        feishin.last = cache_key

    feishin.position = info["position"]

# Mainloop
if __name__ == "__main__":
    while True:
        try:
            update()
            sleep(UPDATE_TIME)

        except KeyboardInterrupt:
            onexit()
            break

        except PipeClosed:
            try:
                rpc.connect()

            except DiscordNotFound:
                sleep(UPDATE_TIME)
