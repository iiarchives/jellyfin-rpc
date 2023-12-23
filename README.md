# Jellyfin/Feishin RPC

Not to be confused with [jellyfin-rpc by Radiicall](https://github.com/Radiicall/jellyfin-rpc).  
This is a Python app that displays the currently playing song from [Jellyfin](https://jellyfin.org/) (or [Feishin](https://github.com/jeffvli/feishin)) on your discord profile.  

This app has two files:
- Jellyfin RPC (for anything Jellyfin related)
- MPRIS RPC (intended for Feishin, or any other MPRIS-based clients)

You will need to customize your configuration depending on the one you will be using.

## Installation

- Install [Python 3.11](https://python.org) or above
- Clone the repository or download the ZIP
- Install dependencies via `python3 -m pip install -r requirements.txt`
- Configure following [Configuration](#configuration)
- Launch via `python3 jellyfin-rpc.py`

## SystemD

```
[Unit]
Description=Jellyfin-RPC Service
After=network.target

[Service]
Type=simple
ExecStart=python3 /path/to/jellyfin-rpc.py

[Install]
WantedBy=default.target
```

## Configuration

All configuration goes in `~/.config/iipython/jellyfin-rpc.toml`.

### Jellyfin

```toml
# The preferred URL of your server (hostnames supported)
url = "http://192.168.0.1:8096"

# Your Jellyfin API key
api_key = "eeeeeeeeeeeeeeeeeeeeeeeeeveeeeeee"

# (optional) Use a public imgproxy server? (needed most of the time)
imageproxy_enabled = true
imageproxy_url = "https://images.iipython.dev"

# (optional) The public URL of your server (for port-forwarded album art)
url_public = "https://jellyfin.yourdomain.com"

# (optional) Fetch album art from MusicBrainz?
musicbrainz_album_art = false

# (optional) Time between Jellyfin requests (defaults to 1 second)
update_time = 0.1
```

### MPRIS (Feishin)

```toml
# The LOCAL URL of your server (hostnames supported)
# If you want discord to use the art url your client sends, set this AND url_public to ""
url = "http://192.168.0.1:8096"

# (optional) Use a public imgproxy server? (needed most of the time)
# Obviously, you can self host your own imgproxy server as desired.
imageproxy_enabled = true
imageproxy_url = "https://images.iipython.dev"

# (optional) The public URL of your server (for port-forwarded album art, passed to imgproxy)
# Leave this BLANK if you don't want to edit the url your client sends
url_public = "https://jellyfin.yourdomain.com"

# (optional) Time between MPRIS updates (defaults to 1 second)
# Recommended to be as fast as possible for your hardware without causing
# a major performance impact.
update_time = 0.1

# (optional) The name your client uses to identify itself over the MPRIS dbus API
# You can usually find this using a dbus client such as qdbus, however milage may vary
# Feel free to submit a PR if you get it working with a custom client
client_name = "Feishin"
```
