#!/usr/bin/env python3
"""
GMod Override Manager
---------------------
Drop an override pack (a folder containing models/ and/or materials/, plus an
optional override.json describing what it changes) into the "overrides" folder
next to this app, hit Refresh, and toggle it on/off.

Enabling installs the pack as a LEGACY addon (addons/ovr_<name>) whose files sit
ABOVE the server's, so model/skin overrides win even on servers you don't host.
Disabling removes it. Changes take effect on the next map load / reconnect
(GMod doesn't hot-swap an already-loaded model in the current session).
"""
import os
import sys
import json
import shutil
import subprocess
import threading
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import urllib.request
import zipfile
import translate_cache
import live_translator

if getattr(sys, "frozen", False):
    # running as a PyInstaller .exe -> use the folder the .exe lives in
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
OVERRIDES_DIR = os.path.join(APP_DIR, "overrides")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
DEFAULT_GMOD = r"C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\garrysmod"
DEFAULT_COMMUNITY_INDEX_URL = "https://raw.githubusercontent.com/VastohLorde/gmod-override-manager/main/community_packs.json"
OLD_COMMUNITY_INDEX_URLS = {
    "https://raw.githubusercontent.com/YOURNAME/gmod-override-packs/main/community_packs.json",
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            cfg = json.load(open(CONFIG_PATH, encoding="utf-8"))
            if cfg.get("community_index_url") in OLD_COMMUNITY_INDEX_URLS:
                cfg["community_index_url"] = DEFAULT_COMMUNITY_INDEX_URL
                save_config(cfg)
            return cfg
        except Exception:
            pass
    return {"gmod_path": DEFAULT_GMOD, "community_index_url": DEFAULT_COMMUNITY_INDEX_URL}


def save_config(cfg):
    try:
        json.dump(cfg, open(CONFIG_PATH, "w", encoding="utf-8"), indent=2)
    except Exception:
        pass


def addons_dir(cfg):
    return os.path.join(cfg.get("gmod_path", DEFAULT_GMOD), "addons")


def slugify(name):
    return "ovr_" + "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")


def pack_folder_name(name):
    cleaned = "".join(c if c.isalnum() or c in " ._-" else "_" for c in name).strip(" ._")
    return cleaned or "Community Pack"


def scan_overrides():
    packs = []
    os.makedirs(OVERRIDES_DIR, exist_ok=True)
    for name in sorted(os.listdir(OVERRIDES_DIR)):
        folder = os.path.join(OVERRIDES_DIR, name)
        if not os.path.isdir(folder):
            continue
        has_content = os.path.isdir(os.path.join(folder, "models")) or os.path.isdir(os.path.join(folder, "materials"))
        if not has_content:
            continue
        meta = {"name": name, "character": "(unspecified)", "skin": "", "description": "", "folder": folder}
        mj = os.path.join(folder, "override.json")
        if os.path.exists(mj):
            try:
                d = json.load(open(mj, encoding="utf-8"))
                for k in ("name", "character", "skin", "description"):
                    if d.get(k):
                        meta[k] = d[k]
            except Exception:
                pass
        meta["slug"] = slugify(meta["name"])
        packs.append(meta)
    return packs


def is_enabled(cfg, pack):
    return os.path.isdir(os.path.join(addons_dir(cfg), pack["slug"]))


def enable(cfg, pack):
    dest = os.path.join(addons_dir(cfg), pack["slug"])
    if os.path.isdir(dest):
        shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest, exist_ok=True)
    for sub in ("models", "materials", "lua"):
        src = os.path.join(pack["folder"], sub)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dest, sub))
    aj = os.path.join(pack["folder"], "addon.json")
    if os.path.exists(aj):
        shutil.copy2(aj, os.path.join(dest, "addon.json"))
    else:
        json.dump({"title": pack["name"], "type": "model", "tags": ["fun"], "ignore": []},
                  open(os.path.join(dest, "addon.json"), "w", encoding="utf-8"))


def disable(cfg, pack):
    dest = os.path.join(addons_dir(cfg), pack["slug"])
    if os.path.isdir(dest):
        shutil.rmtree(dest, ignore_errors=True)


def read_json_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "GModOverrideManager/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read(2_000_000)
    return json.loads(data.decode("utf-8"))


def normalize_community_index(data):
    packs = data.get("packs") if isinstance(data, dict) else data
    if not isinstance(packs, list):
        raise ValueError("Community index must be a JSON array or an object with a 'packs' array.")
    out = []
    for item in packs:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        url = str(item.get("download_url") or item.get("url") or "").strip()
        if not name or not url:
            continue
        out.append({
            "name": name,
            "character": str(item.get("character") or "(unspecified)"),
            "skin": str(item.get("skin") or item.get("version") or ""),
            "version": str(item.get("version") or ""),
            "author": str(item.get("author") or ""),
            "description": str(item.get("description") or ""),
            "download_url": url,
        })
    return out


def safe_extract_zip(zip_path, dest_dir):
    dest_abs = os.path.abspath(dest_dir)
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if not names:
            raise ValueError("Downloaded ZIP is empty.")
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in name.split("/"):
                raise ValueError(f"Unsafe ZIP path: {info.filename}")
            target = os.path.abspath(os.path.join(dest_abs, *name.split("/")))
            if os.path.commonpath([dest_abs, target]) != dest_abs:
                raise ValueError(f"Unsafe ZIP path: {info.filename}")
        zf.extractall(dest_abs)


def find_pack_root(folder):
    if os.path.isdir(os.path.join(folder, "models")) or os.path.isdir(os.path.join(folder, "materials")):
        return folder
    children = [
        os.path.join(folder, name)
        for name in os.listdir(folder)
        if os.path.isdir(os.path.join(folder, name))
    ]
    if len(children) == 1:
        child = children[0]
        if os.path.isdir(os.path.join(child, "models")) or os.path.isdir(os.path.join(child, "materials")):
            return child
    return folder


def install_community_pack(pack):
    os.makedirs(OVERRIDES_DIR, exist_ok=True)
    folder_name = pack_folder_name(pack["name"])
    final_dir = os.path.join(OVERRIDES_DIR, folder_name)
    req = urllib.request.Request(pack["download_url"], headers={"User-Agent": "GModOverrideManager/1.0"})
    with tempfile.TemporaryDirectory() as td:
        zip_path = os.path.join(td, "pack.zip")
        with urllib.request.urlopen(req, timeout=60) as resp, open(zip_path, "wb") as out:
            shutil.copyfileobj(resp, out)
        extract_dir = os.path.join(td, "extract")
        os.makedirs(extract_dir, exist_ok=True)
        safe_extract_zip(zip_path, extract_dir)
        pack_root = find_pack_root(extract_dir)
        if not (os.path.isdir(os.path.join(pack_root, "models")) or os.path.isdir(os.path.join(pack_root, "materials"))):
            raise ValueError("Pack ZIP must contain a folder with models/ and/or materials/.")
        if os.path.isdir(final_dir):
            shutil.rmtree(final_dir)
        shutil.copytree(pack_root, final_dir)
    override_json = os.path.join(final_dir, "override.json")
    if not os.path.exists(override_json):
        meta = {
            "name": pack["name"],
            "character": pack.get("character") or "(unspecified)",
            "skin": pack.get("skin") or pack.get("version") or "Community pack",
            "description": pack.get("description") or "",
        }
        json.dump(meta, open(override_json, "w", encoding="utf-8"), indent=2)
    return final_dir


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.packs = []
        self.title("GMod Override Manager")
        self.geometry("760x460")
        self.minsize(640, 360)
        self._build()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="GMod folder:").pack(side="left")
        self.path_var = tk.StringVar(value=self.cfg.get("gmod_path", DEFAULT_GMOD))
        ttk.Entry(top, textvariable=self.path_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(top, text="Browse", command=self.browse).pack(side="left")
        ttk.Button(top, text="Save", command=self.save_path).pack(side="left", padx=4)

        mid = ttk.Frame(self, padding=(8, 0))
        mid.pack(fill="both", expand=True)
        cols = ("name", "character", "skin", "status")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="browse")
        for c, w, t in (("name", 180, "Override"), ("character", 170, "Character"),
                        ("skin", 150, "Skin / variant"), ("status", 90, "Status")):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="w")
        self.tree.tag_configure("on", foreground="#1a7f1a")
        self.tree.tag_configure("off", foreground="#999999")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: self.toggle())
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.update_desc())
        sb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        sb.pack(side="left", fill="y")
        self.tree.configure(yscrollcommand=sb.set)

        self.desc = tk.StringVar(value="Select an override to see details.")
        ttk.Label(self, textvariable=self.desc, padding=8, wraplength=720,
                  foreground="#444").pack(fill="x")

        bot = ttk.Frame(self, padding=8)
        bot.pack(fill="x")
        ttk.Button(bot, text="Enable", command=lambda: self.set_state(True)).pack(side="left")
        ttk.Button(bot, text="Disable", command=lambda: self.set_state(False)).pack(side="left", padx=4)
        ttk.Button(bot, text="Delete", command=self.delete_selected).pack(side="left")
        ttk.Button(bot, text="Toggle (dbl-click)", command=self.toggle).pack(side="left")
        ttk.Button(bot, text="Open overrides folder", command=self.open_overrides).pack(side="left", padx=4)
        ttk.Button(bot, text="Community Packs", command=self.community_packs).pack(side="left")
        ttk.Button(bot, text="Refresh", command=self.refresh).pack(side="right")
        ttk.Button(bot, text="Tutorial", command=self.show_tutorial).pack(side="right", padx=4)

        bot2 = ttk.Frame(self, padding=(8, 0, 8, 8))
        bot2.pack(fill="x")
        ttk.Label(bot2, text="Live Translator (English):").pack(side="left")
        ttk.Button(bot2, text="Enable", command=self.lt_enable).pack(side="left", padx=4)
        ttk.Button(bot2, text="Disable", command=self.lt_disable).pack(side="left")
        self.lt_status = tk.StringVar(value="")
        ttk.Label(bot2, textvariable=self.lt_status, foreground="#1a7f1a").pack(side="left", padx=8)

        bot3 = ttk.Frame(self, padding=(8, 0, 8, 8))
        bot3.pack(fill="x")
        ttk.Button(bot3, text="Translate cache (one-shot)", command=self.translate_game).pack(side="left")
        ttk.Button(bot3, text="Undo cache translation", command=self.untranslate_game).pack(side="left", padx=4)
        ttk.Label(bot3, text="(live = legacy addon, swaps text every frame; cache = edits downloaded Lua once)",
                  foreground="#777").pack(side="left", padx=6)
        self.note = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.note, padding=(8, 0, 8, 8), foreground="#a05").pack(fill="x")

    TUTORIAL = (
        "GMOD OVERRIDE MANAGER — QUICK TUTORIAL\n"
        "======================================\n\n"
        "1) SET YOUR GMOD FOLDER\n"
        "   The top box should point to:\n"
        "   ...\\steamapps\\common\\GarrysMod\\garrysmod\n"
        "   If it's wrong, click Browse, pick that folder, then Save.\n\n"
        "2) TURN AN OVERRIDE ON/OFF\n"
        "   Click an override in the list, then Enable or Disable\n"
        "   (or just double-click the row to toggle).\n"
        "   The Status column shows ENABLED / disabled.\n\n"
        "3) WHEN IT TAKES EFFECT\n"
        "   Changes apply on the next map load or server RECONNECT —\n"
        "   GMod can't swap a model already loaded in your current game.\n"
        "   So: toggle here, then reconnect to the server.\n\n"
        "4) ADD A NEW OVERRIDE (drag & drop)\n"
        "   Click 'Open overrides folder'. Drop a pack FOLDER inside it,\n"
        "   then click Refresh. A pack looks like:\n"
        "       MyOverride/\n"
        "         override.json   (name, character, skin, description)\n"
        "         models/...      (model files)\n"
        "         materials/...   (textures / sprites)\n\n"
        "5) ADD A COMMUNITY PACK\n"
        "   Click 'Community Packs', paste or keep an index URL, then Refresh.\n"
        "   Pick a pack and click Install. It downloads into overrides/ like\n"
        "   a normal dropped-in pack, then you can Enable it.\n\n"
        "6) WHO SEES IT\n"
        "   Only YOU see your overrides. Friends need the same pack\n"
        "   enabled on their own copy (share this whole folder/app).\n\n"
        "WHY A LEGACY ADDON (not Workshop)?\n"
        "   Enabling installs the pack into addons\\ovr_<name>. These files\n"
        "   sit ABOVE the server's, so the override wins even on servers you\n"
        "   don't host. A Workshop subscription can't do that."
    )

    def show_tutorial(self):
        win = tk.Toplevel(self)
        win.title("Tutorial")
        win.geometry("560x520")
        win.transient(self)
        frame = ttk.Frame(win, padding=10)
        frame.pack(fill="both", expand=True)
        txt = tk.Text(frame, wrap="word", font=("Consolas", 10), borderwidth=0)
        sb = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)
        txt.insert("1.0", self.TUTORIAL)
        txt.configure(state="disabled")
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=8)

    def browse(self):
        d = filedialog.askdirectory(title="Select your ...\\GarrysMod\\garrysmod folder")
        if d:
            self.path_var.set(d)
            self.save_path()

    def save_path(self):
        self.cfg["gmod_path"] = self.path_var.get().strip()
        save_config(self.cfg)
        self.refresh()

    def open_overrides(self):
        os.makedirs(OVERRIDES_DIR, exist_ok=True)
        try:
            os.startfile(OVERRIDES_DIR)  # noqa (Windows)
        except Exception:
            messagebox.showinfo("Overrides folder", OVERRIDES_DIR)

    def community_packs(self):
        win = tk.Toplevel(self)
        win.title("Community Packs")
        win.geometry("820x520")
        win.minsize(680, 420)
        win.transient(self)

        packs = []
        selected = {"index": None}

        top = ttk.Frame(win, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Index URL:").pack(side="left")
        url_var = tk.StringVar(value=self.cfg.get("community_index_url", DEFAULT_COMMUNITY_INDEX_URL))
        ttk.Entry(top, textvariable=url_var).pack(side="left", fill="x", expand=True, padx=6)

        mid = ttk.Frame(win, padding=(8, 0))
        mid.pack(fill="both", expand=True)
        cols = ("name", "character", "version", "author")
        tree = ttk.Treeview(mid, columns=cols, show="headings", selectmode="browse")
        for c, w, t in (("name", 220, "Pack"), ("character", 170, "Character"),
                        ("version", 90, "Version"), ("author", 120, "Author")):
            tree.heading(c, text=t)
            tree.column(c, width=w, anchor="w")
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(mid, orient="vertical", command=tree.yview)
        sb.pack(side="left", fill="y")
        tree.configure(yscrollcommand=sb.set)

        detail = tk.StringVar(value="Refresh to load community packs.")
        ttk.Label(win, textvariable=detail, padding=8, wraplength=780, foreground="#444").pack(fill="x")
        status = tk.StringVar(value="")
        ttk.Label(win, textvariable=status, padding=(8, 0), foreground="#a05").pack(fill="x")

        def selected_pack():
            sel = tree.selection()
            if not sel:
                return None
            return packs[int(sel[0])]

        def update_detail(_event=None):
            p = selected_pack()
            selected["index"] = int(tree.selection()[0]) if tree.selection() else None
            if not p:
                detail.set("Select a community pack to see details.")
                return
            bits = [p["name"]]
            if p.get("version"):
                bits.append(f"v{p['version']}")
            if p.get("author"):
                bits.append(f"by {p['author']}")
            desc = p.get("description") or "(no description)"
            detail.set(f"{' - '.join(bits)}\nOverrides: {p.get('character')} ({p.get('skin')})\n{desc}")

        def load_index():
            url = url_var.get().strip()
            if not url:
                messagebox.showinfo("Index URL", "Enter a community pack index URL first.")
                return
            self.cfg["community_index_url"] = url
            save_config(self.cfg)
            tree.delete(*tree.get_children())
            packs.clear()
            detail.set("Loading community packs...")
            status.set("")
            win.update_idletasks()
            try:
                loaded = normalize_community_index(read_json_url(url))
            except Exception as e:
                detail.set("Could not load community packs.")
                status.set(str(e))
                return
            packs.extend(loaded)
            for i, p in enumerate(packs):
                tree.insert("", "end", iid=str(i),
                            values=(p["name"], p["character"], p.get("version") or p.get("skin"), p.get("author")))
            detail.set(f"Loaded {len(packs)} community pack(s).")
            status.set("")

        def install_selected():
            p = selected_pack()
            if not p:
                messagebox.showinfo("Pick one", "Select a community pack first.")
                return
            if not messagebox.askyesno("Install Community Pack",
                                       f"Download and install '{p['name']}' into the overrides folder?\n\n"
                                       "If a local pack with the same name exists, it will be replaced."):
                return
            status.set(f"Installing {p['name']}...")
            win.update_idletasks()

            def work():
                try:
                    folder = install_community_pack(p)
                    self.after(0, lambda: (
                        status.set(f"Installed to {folder}"),
                        self.refresh(),
                        messagebox.showinfo("Community Packs", f"Installed '{p['name']}'.\n\nSelect it in the main list and click Enable.")
                    ))
                except Exception as e:
                    msg = str(e)
                    self.after(0, lambda: status.set(msg))
            threading.Thread(target=work, daemon=True).start()

        tree.bind("<<TreeviewSelect>>", update_detail)
        tree.bind("<Double-1>", lambda _e: install_selected())

        bot = ttk.Frame(win, padding=8)
        bot.pack(fill="x")
        ttk.Button(bot, text="Refresh", command=load_index).pack(side="left")
        ttk.Button(bot, text="Install Selected", command=install_selected).pack(side="left", padx=4)
        ttk.Button(bot, text="Close", command=win.destroy).pack(side="right")
        win.after(100, load_index)

    def refresh(self):
        self.packs = scan_overrides()
        self.tree.delete(*self.tree.get_children())
        ad = addons_dir(self.cfg)
        ok = os.path.isdir(ad)
        for i, p in enumerate(self.packs):
            on = is_enabled(self.cfg, p) if ok else False
            self.tree.insert("", "end", iid=str(i),
                             values=(p["name"], p["character"], p["skin"],
                                     "ENABLED" if on else "disabled"),
                             tags=("on" if on else "off",))
        if not ok:
            self.note.set("GMod 'addons' folder not found — set the correct GMod folder above.")
        elif not self.packs:
            self.note.set("No override packs found. Drop a pack folder into the 'overrides' folder, then Refresh.")
        else:
            self.note.set("Tip: changes apply on next map load / server reconnect, not mid-session.")
        self.lt_refresh()

    def selected(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self.packs[int(sel[0])]

    def update_desc(self):
        p = self.selected()
        if p:
            d = p.get("description") or "(no description)"
            self.desc.set(f"{p['name']} — overrides {p['character']} ({p['skin']}).  {d}")

    def set_state(self, want_on):
        p = self.selected()
        if not p:
            messagebox.showinfo("Pick one", "Select an override first.")
            return
        if not os.path.isdir(addons_dir(self.cfg)):
            messagebox.showerror("GMod not found", "Set the correct GMod folder first.")
            return
        try:
            if want_on:
                enable(self.cfg, p)
            else:
                disable(self.cfg, p)
        except Exception as e:
            messagebox.showerror("Error", str(e))
        self.refresh()

    def delete_selected(self):
        p = self.selected()
        if not p:
            messagebox.showinfo("Pick one", "Select an override first.")
            return
        folder = os.path.abspath(p["folder"])
        overrides = os.path.abspath(OVERRIDES_DIR)
        if os.path.commonpath([overrides, folder]) != overrides:
            messagebox.showerror("Delete blocked", "That override folder is outside the overrides folder.")
            return
        if not messagebox.askyesno("Delete Override",
                                   f"Delete local override '{p['name']}'?\n\n"
                                   "If it is enabled, it will be disabled first. This cannot be undone."):
            return
        try:
            disable(self.cfg, p)
            shutil.rmtree(folder)
        except Exception as e:
            messagebox.showerror("Delete failed", str(e))
            return
        self.refresh()
        self.desc.set("Select an override to see details.")

    def toggle(self):
        p = self.selected()
        if not p:
            return
        self.set_state(not is_enabled(self.cfg, p))

    def lt_refresh(self):
        on = live_translator.is_installed(self.cfg.get("gmod_path", DEFAULT_GMOD))
        self.lt_status.set("ENABLED (restart GMod)" if on else "disabled")

    def lt_enable(self):
        gp = self.cfg.get("gmod_path", DEFAULT_GMOD)
        if not os.path.isdir(os.path.join(gp, "addons")):
            messagebox.showerror("GMod not found", "Set the correct GMod folder first.")
            return
        tj = self._trans_json()
        if not tj:
            return
        try:
            n = live_translator.install(gp, tj)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        self.lt_refresh()
        messagebox.showinfo("Live Translator",
                            f"Enabled ({n} phrases) as a legacy addon.\n\n"
                            "IMPORTANT: fully RESTART GMod (legacy addons load at startup), then join.\n"
                            "You should see a green 'Live Translator active' indicator top-left for ~20s.")

    def lt_disable(self):
        live_translator.uninstall(self.cfg.get("gmod_path", DEFAULT_GMOD))
        self.lt_refresh()
        messagebox.showinfo("Live Translator", "Disabled (removed). Restart GMod to apply.")

    def _trans_json(self):
        p = os.path.expanduser(r"~\Downloads\translations.json")
        if os.path.exists(p):
            return p
        return filedialog.askopenfilename(title="Select translations.json",
                                          filetypes=[("JSON", "*.json")])

    def translate_game(self):
        gp = self.cfg.get("gmod_path", DEFAULT_GMOD)
        if not os.path.isdir(os.path.join(gp, "cache", "lua")):
            messagebox.showerror("No cache", "GMod cache/lua not found. Set the correct GMod folder, and join the server once so it caches the Lua.")
            return
        tj = self._trans_json()
        if not tj:
            return
        if not messagebox.askyesno("Translate", "Translate GMod's cached server Lua to English?\n\nA backup is made the first time. You can Undo afterwards.\n(If the game re-downloads on join, the server is re-verifying the cache and this can't stick.)"):
            return
        self.note.set("Translating cached Lua… (this can take a few seconds)")
        self.update_idletasks()

        def work():
            try:
                scanned, changed = translate_cache.translate_dir(gp, tj, log=lambda *_: None)
                msg = f"Translated {changed} of {scanned} cached Lua files.\n\nReconnect to the server to see English. If it shows Russian again, the server re-verifies the cache (nothing client-side can change it)."
                self.after(0, lambda: (self.note.set(f"Done: translated {changed}/{scanned} cache files."), messagebox.showinfo("Translate", msg)))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Translate failed", str(e)))
        threading.Thread(target=work, daemon=True).start()

    def untranslate_game(self):
        gp = self.cfg.get("gmod_path", DEFAULT_GMOD)
        if not os.path.isdir(os.path.join(gp, "cache", "lua", "..", "lua_backup_translate")):
            pass
        translate_cache.restore(gp, log=lambda *_: None)
        self.note.set("Restored cached Lua from backup (translation undone).")
        messagebox.showinfo("Undo", "Restored the original cached Lua from backup.")


if __name__ == "__main__":
    App().mainloop()
