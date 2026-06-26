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
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

if getattr(sys, "frozen", False):
    # running as a PyInstaller .exe -> use the folder the .exe lives in
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
OVERRIDES_DIR = os.path.join(APP_DIR, "overrides")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
DEFAULT_GMOD = r"C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\garrysmod"


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            return json.load(open(CONFIG_PATH, encoding="utf-8"))
        except Exception:
            pass
    return {"gmod_path": DEFAULT_GMOD}


def save_config(cfg):
    try:
        json.dump(cfg, open(CONFIG_PATH, "w", encoding="utf-8"), indent=2)
    except Exception:
        pass


def addons_dir(cfg):
    return os.path.join(cfg.get("gmod_path", DEFAULT_GMOD), "addons")


def slugify(name):
    return "ovr_" + "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")


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
        ttk.Button(bot, text="Toggle (dbl-click)", command=self.toggle).pack(side="left")
        ttk.Button(bot, text="Open overrides folder", command=self.open_overrides).pack(side="left", padx=4)
        ttk.Button(bot, text="Refresh", command=self.refresh).pack(side="right")
        ttk.Button(bot, text="Tutorial", command=self.show_tutorial).pack(side="right", padx=4)
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
        "5) WHO SEES IT\n"
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

    def toggle(self):
        p = self.selected()
        if not p:
            return
        self.set_state(not is_enabled(self.cfg, p))


if __name__ == "__main__":
    App().mainloop()
