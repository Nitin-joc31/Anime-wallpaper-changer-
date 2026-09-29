"""
WallDrop v2 — Online Anime Wallpaper Changer
Sources: Wallhaven (free) + Alpha Coders (API key)
Zero background process — uses Windows Task Scheduler.
"""

import os, sys, json, random, ctypes, subprocess, threading, urllib.request, urllib.parse
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_FILE = Path(os.environ.get("APPDATA", Path.home())) / "WallDrop" / "config.json"
CACHE_DIR   = Path(os.environ.get("APPDATA", Path.home())) / "WallDrop" / "cache"
CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
TASK_NAME   = "WallDropOnline"
CONFIG_WARNING = None

# ── Wallhaven API (free, no key needed for SFW anime) ────────────────────────
WALLHAVEN_SEARCH = "https://wallhaven.cc/api/v1/search"
WALLHAVEN_CATEGORIES = {
    "Anime (General)":    ("010", ""),
    "Anime – Top Rated":  ("010", "toplist"),
    "Anime – Latest":     ("010", "date_added"),
    "Anime – Landscape":  ("010", ""),   # filtered by ratio
}

# ── Alpha Coders API ──────────────────────────────────────────────────────────
ALPHACODERS_BASE = "https://api.alphacoders.com/3.0"
ALPHACODERS_ANIME_CAT = "3"   # Anime category ID

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_config():
    global CONFIG_WARNING
    CONFIG_WARNING = None
    if CONFIG_FILE.exists():
        try:
            config = json.loads(CONFIG_FILE.read_text())
            if isinstance(config, dict):
                return config
            raise ValueError("Configuration must contain a JSON object.")
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            backup = CONFIG_FILE.with_name(CONFIG_FILE.name + ".corrupt")
            suffix = 1
            while backup.exists():
                backup = CONFIG_FILE.with_name(f"{CONFIG_FILE.name}.corrupt.{suffix}")
                suffix += 1
            try:
                CONFIG_FILE.replace(backup)
                CONFIG_WARNING = (
                    f"The configuration file was invalid and has been preserved as "
                    f"{backup}. Default settings will be used."
                )
            except OSError as backup_error:
                CONFIG_WARNING = (
                    f"The configuration file could not be read ({exc}) or preserved "
                    f"({backup_error}). It will not be overwritten."
                )
    return {
        "source":           "wallhaven",
        "wallhaven_query":  "anime",
        "wallhaven_sort":   "random",
        "alphacoders_key":  "",
        "alphacoders_sort": "random",
        "interval_minutes": 30,
        "resolution":       "1920x1080",
        "last_wallpaper":   "",
        "page":             1,
    }

def save_config(cfg):
    if CONFIG_WARNING and CONFIG_FILE.exists():
        raise OSError(CONFIG_WARNING)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

def set_wallpaper(path: str) -> bool:
    return ctypes.windll.user32.SystemParametersInfoW(20, 0, str(path), 3) != 0

def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "WallDrop/2.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def download_image(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "WallDrop/2.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            dest.write_bytes(r.read())
        return True
    except Exception:
        return False

def clear_cache():
    for f in CACHE_DIR.glob("*"):
        try: f.unlink()
        except: pass

# ── Wallhaven fetcher ─────────────────────────────────────────────────────────
def fetch_wallhaven(cfg: dict):
    query  = cfg.get("wallhaven_query", "anime")
    sort   = cfg.get("wallhaven_sort", "random")
    res    = cfg.get("resolution", "1920x1080")
    page   = cfg.get("page", 1)

    params = {
        "q":           query,
        "categories":  "010",        # anime only
        "purity":      "100",        # SFW only
        "sorting":     sort if sort != "random" else "random",
        "resolutions": res,
        "page":        page,
    }
    url = WALLHAVEN_SEARCH + "?" + urllib.parse.urlencode(params)
    data = fetch_json(url)
    walls = data.get("data", [])
    if not walls:
        raise ValueError("No wallpapers found. Try a different query or resolution.")
    wall = random.choice(walls)
    img_url = wall["path"]
    ext = img_url.rsplit(".", 1)[-1]
    dest = CACHE_DIR / f"walldrop_wh.{ext}"
    if not download_image(img_url, dest):
        raise ValueError(f"Failed to download image from Wallhaven.")
    return str(dest), wall.get("url", ""), wall.get("id", "")

# ── Alpha Coders fetcher ──────────────────────────────────────────────────────
def fetch_alphacoders(cfg: dict):
    key  = cfg.get("alphacoders_key", "").strip()
    sort = cfg.get("alphacoders_sort", "random")
    if not key:
        raise ValueError("Alpha Coders API key not set.")

    method = "random" if sort == "random" else "newest"
    url = f"{ALPHACODERS_BASE}?auth={key}&method={method}&category_id={ALPHACODERS_ANIME_CAT}&type=desktop"
    data = fetch_json(url)
    if not data.get("success"):
        raise ValueError(f"Alpha Coders API error: {data.get('error', 'Unknown error')}")
    walls = data.get("wallpapers", [])
    if not walls:
        raise ValueError("No wallpapers returned from Alpha Coders.")
    wall = random.choice(walls)
    img_url = wall.get("url_image") or wall.get("url")
    ext = img_url.rsplit(".", 1)[-1].split("?")[0] or "jpg"
    dest = CACHE_DIR / f"walldrop_ac.{ext}"
    if not download_image(img_url, dest):
        raise ValueError("Failed to download image from Alpha Coders.")
    return str(dest), wall.get("url_page", ""), str(wall.get("id", ""))

# ── Main apply logic ──────────────────────────────────────────────────────────
def apply_next_wallpaper(cfg=None):
    if cfg is None:
        cfg = load_config()
    source = cfg.get("source", "wallhaven")
    try:
        if source == "alphacoders":
            path, page_url, wid = fetch_alphacoders(cfg)
        else:
            path, page_url, wid = fetch_wallhaven(cfg)
        ok = set_wallpaper(path)
        if ok:
            cfg["last_wallpaper"] = path
            cfg["last_url"] = page_url
            save_config(cfg)
            return True, path, page_url
        return False, "Failed to set wallpaper.", ""
    except Exception as e:
        return False, str(e), ""

# ── Task Scheduler ────────────────────────────────────────────────────────────
def register_task(interval_minutes: int):
    python_exe  = sys.executable
    script_path = os.path.abspath(__file__)
    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <TimeTrigger>
      <Repetition>
        <Interval>PT{interval_minutes}M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>2024-01-01T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
    <LogonTrigger><Enabled>true</Enabled></LogonTrigger>
  </Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>"{script_path}" --apply</Arguments>
    </Exec>
  </Actions>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT2M</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
</Task>"""
    xml_path = CONFIG_FILE.parent / "task.xml"
    xml_path.write_text(xml, encoding="utf-16")
    r = subprocess.run(["schtasks", "/Create", "/TN", TASK_NAME, "/XML", str(xml_path), "/F"],
                       capture_output=True, text=True)
    return r.returncode == 0, r.stdout + r.stderr

def unregister_task():
    r = subprocess.run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
                       capture_output=True, text=True)
    return r.returncode == 0

def task_exists():
    r = subprocess.run(["schtasks", "/Query", "/TN", TASK_NAME],
                       capture_output=True, text=True)
    return r.returncode == 0

# ── GUI ───────────────────────────────────────────────────────────────────────
C = {
    "bg":      "#0c0c10",
    "panel":   "#13131c",
    "border":  "#1e1e2e",
    "accent":  "#c084fc",     # purple
    "accent2": "#f472b6",     # pink
    "green":   "#4ade80",
    "red":     "#f87171",
    "yellow":  "#fbbf24",
    "text":    "#e2e2f0",
    "muted":   "#6b6b8a",
    "dim":     "#2a2a3d",
}

def styled_btn(parent, text, cmd, bg, fg, padx=14, pady=8):
    return tk.Button(parent, text=text, command=cmd,
                     font=("Courier New", 9, "bold"), bg=bg, fg=fg,
                     relief="flat", bd=0, padx=padx, pady=pady,
                     cursor="hand2", activebackground=bg, activeforeground=fg)

class WallDropApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WallDrop v2 — Anime Wallpapers")
        self.root.geometry("660x700")
        self.root.resizable(False, False)
        self.root.configure(bg=C["bg"])
        self.cfg = load_config()
        self._build()
        if CONFIG_WARNING:
            warning = CONFIG_WARNING
            self.root.after(
                0,
                lambda: messagebox.showwarning("WallDrop Configuration", warning),
            )
        self._refresh_status()

    def _section(self, parent, text, pady=(20, 6)):
        tk.Frame(parent, bg=C["bg"], height=1).pack(fill="x", padx=28, pady=(pady[0], 0))
        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="x", padx=28, pady=(4, pady[1]))
        tk.Label(row, text=text, font=("Courier New", 8, "bold"),
                 fg=C["accent"], bg=C["bg"]).pack(side="left")
        tk.Frame(row, bg=C["border"], height=1).pack(side="left", fill="x", expand=True, padx=(10, 0), pady=6)

    def _build(self):
        root = self.root

        # Header
        h = tk.Frame(root, bg=C["bg"], pady=22)
        h.pack(fill="x", padx=28)
        tk.Label(h, text="◈ WALLDROP", font=("Courier New", 24, "bold"),
                 fg=C["accent"], bg=C["bg"]).pack(side="left")
        tk.Label(h, text=" v2", font=("Courier New", 12),
                 fg=C["accent2"], bg=C["bg"]).pack(side="left", pady=8)
        tk.Label(h, text="anime wallpapers from the internet",
                 font=("Courier New", 8), fg=C["muted"], bg=C["bg"]).pack(side="right", pady=10)

        # ── Source ──
        self._section(root, "01 — SOURCE")
        src_row = tk.Frame(root, bg=C["bg"])
        src_row.pack(fill="x", padx=28, pady=(0, 4))
        self.source_var = tk.StringVar(value=self.cfg.get("source", "wallhaven"))
        for val, label, sub in [
            ("wallhaven",    "WALLHAVEN",      "free · no key needed · huge anime library"),
            ("alphacoders",  "ALPHA CODERS",   "requires API key · premium quality"),
        ]:
            f = tk.Frame(src_row, bg=C["bg"])
            f.pack(side="left", padx=(0, 12))
            rb = tk.Radiobutton(f, text=label, variable=self.source_var, value=val,
                                command=self._on_source_change,
                                font=("Courier New", 10, "bold"),
                                bg=C["bg"], fg=C["text"], selectcolor=C["bg"],
                                activebackground=C["bg"], activeforeground=C["accent"],
                                indicatoron=0, relief="flat", bd=0,
                                padx=14, pady=8, cursor="hand2",
                                highlightthickness=1, highlightbackground=C["border"],
                                highlightcolor=C["accent"])
            rb.pack()
            tk.Label(f, text=sub, font=("Courier New", 7), fg=C["muted"], bg=C["bg"]).pack()

        # ── Wallhaven settings ──
        self.wh_frame = tk.Frame(root, bg=C["bg"])
        self.wh_frame.pack(fill="x", padx=28)

        self._section(self.wh_frame, "02 — SEARCH QUERY", pady=(10, 4))
        qrow = tk.Frame(self.wh_frame, bg=C["bg"])
        qrow.pack(fill="x", padx=0, pady=(0, 8))
        self.query_var = tk.StringVar(value=self.cfg.get("wallhaven_query", "anime"))
        qe = tk.Entry(qrow, textvariable=self.query_var,
                      font=("Courier New", 10), bg=C["panel"], fg=C["text"],
                      insertbackground=C["accent"], relief="flat", bd=0,
                      highlightthickness=1, highlightbackground=C["border"],
                      highlightcolor=C["accent"])
        qe.pack(side="left", fill="x", expand=True, ipady=8, ipadx=10)
        tk.Label(qrow, text="  e.g: naruto, ghibli, cyberpunk anime",
                 font=("Courier New", 8), fg=C["muted"], bg=C["bg"]).pack(side="left")

        self._section(self.wh_frame, "03 — SORT BY", pady=(10, 4))
        sort_row = tk.Frame(self.wh_frame, bg=C["bg"])
        sort_row.pack(fill="x", pady=(0, 8))
        self.sort_var = tk.StringVar(value=self.cfg.get("wallhaven_sort", "random"))
        for val, lbl in [("random","RANDOM"),("toplist","TOP RATED"),("date_added","LATEST"),("views","MOST VIEWED"),("favorites","MOST SAVED")]:
            tk.Radiobutton(sort_row, text=lbl, variable=self.sort_var, value=val,
                           font=("Courier New", 8, "bold"),
                           bg=C["bg"], fg=C["muted"], selectcolor=C["bg"],
                           activebackground=C["bg"], activeforeground=C["accent"],
                           indicatoron=0, relief="flat", bd=0, padx=10, pady=6,
                           cursor="hand2", highlightthickness=1,
                           highlightbackground=C["border"], highlightcolor=C["accent"]
                           ).pack(side="left", padx=(0, 6))

        # ── Alpha Coders settings ──
        self.ac_frame = tk.Frame(root, bg=C["bg"])
        # (shown/hidden based on source selection)
        self._section(self.ac_frame, "02 — ALPHA CODERS API KEY", pady=(10, 4))
        key_row = tk.Frame(self.ac_frame, bg=C["bg"])
        key_row.pack(fill="x", pady=(0, 4))
        self.key_var = tk.StringVar(value=self.cfg.get("alphacoders_key", ""))
        tk.Entry(key_row, textvariable=self.key_var, show="•",
                 font=("Courier New", 10), bg=C["panel"], fg=C["text"],
                 insertbackground=C["accent"], relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=C["border"],
                 highlightcolor=C["accent"]).pack(fill="x", ipady=8, ipadx=10)
        tk.Label(self.ac_frame,
                 text="  Get a free key at: https://api.alphacoders.com",
                 font=("Courier New", 8), fg=C["muted"], bg=C["bg"]).pack(anchor="w", pady=(2, 8))

        # ── Resolution ──
        self._section(root, "— RESOLUTION", pady=(10, 4))
        res_row = tk.Frame(root, bg=C["bg"])
        res_row.pack(fill="x", padx=28, pady=(0, 8))
        self.res_var = tk.StringVar(value=self.cfg.get("resolution", "1920x1080"))
        for res in ["1280x720", "1920x1080", "2560x1440", "3840x2160"]:
            tk.Radiobutton(res_row, text=res, variable=self.res_var, value=res,
                           font=("Courier New", 8, "bold"),
                           bg=C["bg"], fg=C["muted"], selectcolor=C["bg"],
                           activebackground=C["bg"], activeforeground=C["accent"],
                           indicatoron=0, relief="flat", bd=0, padx=10, pady=6,
                           cursor="hand2", highlightthickness=1,
                           highlightbackground=C["border"], highlightcolor=C["accent"]
                           ).pack(side="left", padx=(0, 6))

        # ── Interval ──
        self._section(root, "— AUTO-CHANGE INTERVAL", pady=(10, 4))
        iv_row = tk.Frame(root, bg=C["bg"])
        iv_row.pack(fill="x", padx=28, pady=(0, 8))
        self.interval_var = tk.IntVar(value=self.cfg.get("interval_minutes", 30))
        for val, lbl in [(5,"5m"),(10,"10m"),(15,"15m"),(30,"30m"),(60,"1h"),(120,"2h"),(360,"6h"),(720,"12h"),(1440,"24h")]:
            tk.Radiobutton(iv_row, text=lbl, variable=self.interval_var, value=val,
                           font=("Courier New", 8, "bold"),
                           bg=C["bg"], fg=C["muted"], selectcolor=C["bg"],
                           activebackground=C["bg"], activeforeground=C["accent"],
                           indicatoron=0, relief="flat", bd=0, padx=8, pady=6,
                           cursor="hand2", highlightthickness=1,
                           highlightbackground=C["border"], highlightcolor=C["accent"]
                           ).pack(side="left", padx=(0, 4))

        # ── Buttons ──
        tk.Frame(root, bg=C["border"], height=1).pack(fill="x", padx=28, pady=(10, 0))
        btn_row = tk.Frame(root, bg=C["bg"], pady=14)
        btn_row.pack(fill="x", padx=28)

        styled_btn(btn_row, "▶  APPLY NOW", self._apply_now, C["accent"], C["bg"]).pack(side="left", padx=(0, 8))
        styled_btn(btn_row, "⏱  ENABLE SCHEDULER", self._enable_sched, C["dim"], C["accent"]).pack(side="left", padx=(0, 8))
        styled_btn(btn_row, "✕  DISABLE", self._disable_sched, C["dim"], C["red"]).pack(side="left")

        # ── Status ──
        tk.Frame(root, bg=C["border"], height=1).pack(fill="x", padx=28)
        st_row = tk.Frame(root, bg=C["bg"], pady=10)
        st_row.pack(fill="x", padx=28)
        self.dot = tk.Label(st_row, text="●", font=("Courier New", 10), bg=C["bg"], fg=C["dim"])
        self.dot.pack(side="left")
        self.status_var = tk.StringVar(value="Checking...")
        tk.Label(st_row, textvariable=self.status_var,
                 font=("Courier New", 9), fg=C["muted"], bg=C["bg"]).pack(side="left", padx=6)

        self.last_var = tk.StringVar(value="")
        tk.Label(root, textvariable=self.last_var,
                 font=("Courier New", 8), fg=C["dim"], bg=C["bg"],
                 wraplength=600, justify="left").pack(anchor="w", padx=28)

        tk.Frame(root, bg=C["border"], height=1).pack(fill="x", padx=28, pady=(10, 0))
        tk.Label(root, text="wallpaper persists after app closes  •  no background process  •  powered by wallhaven.cc / alphacoders.com",
                 font=("Courier New", 7), fg=C["dim"], bg=C["bg"]).pack(pady=8)

        self._on_source_change()

    def _on_source_change(self):
        src = self.source_var.get()
        if src == "wallhaven":
            self.wh_frame.pack(fill="x", padx=28)
            self.ac_frame.pack_forget()
        else:
            self.ac_frame.pack(fill="x", padx=28)
            self.wh_frame.pack_forget()

    def _save_settings(self):
        self.cfg["source"]           = self.source_var.get()
        self.cfg["wallhaven_query"]  = self.query_var.get().strip() or "anime"
        self.cfg["wallhaven_sort"]   = self.sort_var.get()
        self.cfg["alphacoders_key"]  = self.key_var.get().strip()
        self.cfg["interval_minutes"] = self.interval_var.get()
        self.cfg["resolution"]       = self.res_var.get()
        try:
            save_config(self.cfg)
        except OSError as exc:
            messagebox.showerror("Configuration Error", str(exc))
            return False
        return True

    def _apply_now(self):
        if not self._save_settings():
            return
        self._set_status("Fetching wallpaper...", C["yellow"])
        def work():
            ok, result, url = apply_next_wallpaper(self.cfg)
            if ok:
                name = os.path.basename(result)
                self._set_status(f"✓ Applied: {name}", C["green"])
                src = "wallhaven.cc" if self.cfg["source"] == "wallhaven" else "alphacoders.com"
                self.root.after(
                    0,
                    lambda: self.last_var.set(
                        f"  Source: {src}  |  Page: {url[:80] if url else 'N/A'}"
                    ),
                )
            else:
                self._set_status(f"✗ {result}", C["red"])
                self.root.after(
                    0, lambda: messagebox.showerror("WallDrop Error", result)
                )
        threading.Thread(target=work, daemon=True).start()

    def _enable_sched(self):
        if not self._save_settings():
            return
        interval = self.interval_var.get()
        ok, msg = register_task(interval)
        if ok:
            self._set_status(f"Scheduler active — every {interval} min + on login.", C["green"], dot=C["green"])
        else:
            messagebox.showerror("Scheduler Error", f"Run as Administrator and try again.\n\n{msg}")
            self._set_status("Scheduler failed — try Run as Administrator.", C["red"])

    def _disable_sched(self):
        ok = unregister_task()
        self._set_status("Scheduler disabled." if ok else "No scheduler found.", C["muted"], dot=C["dim"])

    def _refresh_status(self):
        def check():
            if task_exists():
                iv = self.cfg.get("interval_minutes", 30)
                self._set_status(f"Scheduler ACTIVE — changes every {iv} min + on login.", C["green"], dot=C["green"])
            else:
                self._set_status("Scheduler not active. Click 'Enable Scheduler'.", C["muted"], dot=C["dim"])
            last = self.cfg.get("last_wallpaper", "")
            if last and os.path.exists(last):
                self.root.after(
                    0,
                    lambda: self.last_var.set(
                        f"  Last: {os.path.basename(last)}"
                    ),
                )
        threading.Thread(target=check, daemon=True).start()

    def _set_status(self, msg, color=None, dot=None):
        color = color or C["muted"]
        def upd():
            self.status_var.set(msg)
            self.dot.config(fg=dot or color)
        self.root.after(0, upd)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--apply" in sys.argv:
        cfg = load_config()
        ok, result, _ = apply_next_wallpaper(cfg)
        sys.exit(0 if ok else 1)
    else:
        root = tk.Tk()
        app = WallDropApp(root)
        root.mainloop()
