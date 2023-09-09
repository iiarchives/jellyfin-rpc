# Jellyfin RPC

Not to be confused with [jellyfin-rpc by Radiicall](https://github.com/Radiicall/jellyfin-rpc).  
This is a Python app that displays the currently playing song from Jellyfin on your discord profile.  

## Installation

- Install [Python 3.10](https://python.org) or above
- Clone the repository or download the ZIP
- Create `~/.config/iipython/jellyfin-rpc.toml`:
```toml
# The preferred URL of your server (hostnames supported)
url = "http://192.168.0.1:8096"

# Your Jellyfin API key
api_key = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"

# (optional) The public URL of your server (for port-forwarded album art)
url_public = "https://jellyfin.yourdomain.com"

# (optional) Fetch album art from MusicBrainz?
musicbrainz_album_art = true

# (optional) Time between Jellyfin requests (defaults to 1 second)
update_time = 0.1
```
- Install dependencies via `python3 -m pip install -r requirements.txt`
- Launch via `python3 jellyfin-rpc.py`

**\* I'll upload a systemd unit for this eventually.**
