# ◈ WallDrop v2 — Online Anime Wallpaper Changer

Automatically downloads and sets anime wallpapers from the internet.
**Zero background process.** Wallpaper stays after app closes.

---

## Requirements

- Windows 10 / 11
- Python 3.7+ from https://www.python.org/downloads/
  ✅ Check "Add Python to PATH" during install
- Internet connection (to fetch wallpapers)

---

## Quick Start

1. Right-click **Install.ps1** and choose **Run with PowerShell**. The installer copies the app to `%LOCALAPPDATA%\WallDrop`, creates a Desktop shortcut, and launches it. Python 3 must already be installed.
2. Choose your source (Wallhaven is free, no key needed)
3. Type a search query like: `naruto`, `ghibli`, `cyberpunk anime`, `one piece`
4. Pick resolution, sort, interval
5. Click **▶ APPLY NOW** to test it
6. Click **⏱ ENABLE SCHEDULER** to automate

---

## Sources

### Wallhaven (Recommended — Free)
- No API key needed
- Massive anime wallpaper library
- SFW only
- Search anything: character names, series, styles

### Alpha Coders
- Requires a free API key from https://api.alphacoders.com
- Sign up → get key → paste it in the app

---

## Privacy and API keys

The Alpha Coders API key is saved as **unencrypted plaintext** in
`%APPDATA%\WallDrop\config.json` so it remains available between launches.
When Alpha Coders is selected, the app sends the key to `api.alphacoders.com`
over HTTPS as part of the API request URL. Avoid using this option on a
shared Windows account or device; use Wallhaven if you do not want to store
an API key. Deleting the WallDrop configuration folder removes the saved key.

## How Automation Works

WallDrop registers a **Windows Task** that:
- Runs every X minutes (your chosen interval)
- Also runs every time you log in
- Downloads a fresh wallpaper → sets it → exits (< 2 seconds)
- **No tray icon. No RAM. No background process.**

---

## Wallpaper Cache

Downloaded wallpapers are saved temporarily at:
`%APPDATA%\WallDrop\cache\`

Only the most recent wallpaper is kept (overwritten each time).
The wallpaper file must exist on disk to stay as your wallpaper.
Do not delete the cache folder if you want your current wallpaper to remain.

---

## Tips

- **Best anime queries for Wallhaven:** `anime landscape`, `anime girl`, `demon slayer`, `attack on titan`, `studio ghibli`, `jujutsu kaisen`, `solo leveling`
- **1920x1080** recommended for most monitors
- **TOP RATED** sort gives the highest quality wallpapers

---

## Uninstall

1. Click **✕ DISABLE** in the app
2. Delete this folder
3. Optionally delete `%APPDATA%\WallDrop\`
