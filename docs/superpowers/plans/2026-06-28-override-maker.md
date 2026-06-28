# Override Maker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local-first Override Maker that creates normal override packs from selected local model files/folders and manually assigned sprite files.

**Architecture:** Keep the pack-building logic in pure helper functions inside `override_manager.py` so it can be unit tested without launching Tkinter. Add a small Tkinter dialog that gathers user input and calls those helpers, then refreshes the existing pack list.

**Tech Stack:** Python 3 standard library, Tkinter, `unittest`, existing single-file `override_manager.py` app.

---

## File Structure

- Modify `override_manager.py`
  - Add constants for model sidecar extensions and sprite assignment slots.
  - Add pure helpers for copying model sidecars, copying material folders, validating sprite files, building `override.json`, and creating the override pack.
  - Add an `App.override_maker()` dialog method.
  - Add an "Override Maker" button to the main window.
  - Update tutorial text to mention the maker.
- Modify `tests/test_retargeting.py`
  - Add tests for the non-UI override maker pipeline.
- No new production files are required because the app already centralizes its behavior in `override_manager.py`.

---

### Task 1: Add Failing Tests for the Pack Builder

**Files:**
- Modify: `tests/test_retargeting.py`

- [ ] **Step 1: Add tests for successful local pack creation and invalid sprite rejection**

Append these tests inside `RetargetingTests`:

```python
    def test_create_override_pack_copies_models_materials_sprites_and_metadata(self):
        source_root = os.path.join(self.tmp, "source")
        os.makedirs(os.path.join(source_root, "models", "player"), exist_ok=True)
        os.makedirs(os.path.join(source_root, "materials", "models", "example"), exist_ok=True)
        model = os.path.join(source_root, "models", "player", "example.mdl")
        arms = os.path.join(source_root, "models", "player", "c_example_arms.mdl")
        for path in (
            model,
            os.path.join(source_root, "models", "player", "example.vvd"),
            os.path.join(source_root, "models", "player", "example.dx90.vtx"),
            arms,
            os.path.join(source_root, "models", "player", "c_example_arms.vvd"),
        ):
            with open(path, "wb") as f:
                f.write(b"model")
        with open(os.path.join(source_root, "materials", "models", "example", "body.vmt"), "wb") as f:
            f.write(b"material")
        sprite = os.path.join(self.tmp, "sprite.vtf")
        with open(sprite, "wb") as f:
            f.write(b"sprite")

        target = om.find_target({}, "Himiko Yumeno")
        output = om.create_override_pack({
            "name": "Maker Pack",
            "character": "Himiko Yumeno",
            "skin": "Local model",
            "description": "Created by test",
            "source_target": target,
            "main_model": model,
            "arms_model": arms,
            "material_root": source_root,
            "sprite_dir": target["sprite_dir"],
            "sprite_assignments": {"Talk 1": {"path": sprite, "filename": "ct_sprite_1.vtf"}},
            "overrides_dir": os.path.join(self.tmp, "overrides"),
        })

        self.assertTrue(os.path.exists(os.path.join(output, "models/dro/player/characters3/char12/char12.mdl")))
        self.assertTrue(os.path.exists(os.path.join(output, "models/dro/player/characters3/char12/char12.vvd")))
        self.assertTrue(os.path.exists(os.path.join(output, "models/dro/player/characters3/char12/c_arms/char12_arms.mdl")))
        self.assertTrue(os.path.exists(os.path.join(output, "materials/models/example/body.vmt")))
        self.assertTrue(os.path.exists(os.path.join(output, "materials/dro/sprites/characters/dr_v3/himiko yumeno/ct_sprite_1.vtf")))
        with open(os.path.join(output, "override.json"), "r", encoding="utf-8") as f:
            meta = json.load(f)
        self.assertEqual("Maker Pack", meta["name"])
        self.assertEqual("Himiko Yumeno", meta["character"])
        self.assertEqual(target, meta["source_target"])

    def test_create_override_pack_rejects_non_game_ready_sprite_files(self):
        source_root = os.path.join(self.tmp, "source")
        os.makedirs(os.path.join(source_root, "models", "player"), exist_ok=True)
        model = os.path.join(source_root, "models", "player", "example.mdl")
        with open(model, "wb") as f:
            f.write(b"model")
        sprite = os.path.join(self.tmp, "sprite.png")
        with open(sprite, "wb") as f:
            f.write(b"not vtf")

        with self.assertRaises(ValueError) as cm:
            om.create_override_pack({
                "name": "Bad Sprite Pack",
                "character": "Himiko Yumeno",
                "skin": "",
                "description": "",
                "source_target": om.find_target({}, "Himiko Yumeno"),
                "main_model": model,
                "arms_model": "",
                "material_root": "",
                "sprite_dir": "materials/dro/sprites/characters/dr_v3/himiko yumeno",
                "sprite_assignments": {"Talk 1": {"path": sprite, "filename": "ct_sprite_1.vtf"}},
                "overrides_dir": os.path.join(self.tmp, "overrides"),
            })
        self.assertIn("game-ready .vtf or .vmt", str(cm.exception))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "overrides", "Bad Sprite Pack")))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
python -m unittest tests.test_retargeting.RetargetingTests.test_create_override_pack_copies_models_materials_sprites_and_metadata tests.test_retargeting.RetargetingTests.test_create_override_pack_rejects_non_game_ready_sprite_files -v
```

Expected: both tests fail with `AttributeError: module 'override_manager' has no attribute 'create_override_pack'`.

---

### Task 2: Implement the Pure Pack Builder

**Files:**
- Modify: `override_manager.py`

- [ ] **Step 1: Add helper constants and functions after `pack_folder_name`**

Add:

```python
MODEL_SIDECAR_EXTS = (".mdl", ".vvd", ".phy", ".dx90.vtx", ".sw.vtx", ".ani")

SPRITE_SLOTS = [
    ("Talk 1", "ct_sprite_1.vtf"),
    ("Talk 2", "ct_sprite_2.vtf"),
    ("Talk 3", "ct_sprite_3.vtf"),
    ("Argue 1", "ct_argue_1.vtf"),
    ("Argue 2", "ct_argue_2.vtf"),
    ("Consent", "ct_consent.vtf"),
    ("Scrum Debate Left", "ct_scrum_left.vtf"),
    ("Scrum Debate Right", "ct_scrum_right.vtf"),
]


def copy_model_sidecars(src_mdl, dest_base):
    src_mdl = os.path.abspath(src_mdl or "")
    if not os.path.isfile(src_mdl):
        raise ValueError("Selected model file does not exist.")
    if os.path.splitext(src_mdl)[1].lower() != ".mdl":
        raise ValueError("Main model must be a .mdl file.")
    src_base, _ = os.path.splitext(src_mdl)
    copied = []
    for ext in MODEL_SIDECAR_EXTS:
        src = src_base + ext
        if not os.path.exists(src):
            continue
        dest = os.path.join(*dest_base.split("/")) + ext
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(dest)
    if not copied:
        raise ValueError("No model files were copied.")
    return copied


def copy_material_root(material_root, output_dir):
    if not material_root:
        return False
    material_dir = os.path.join(material_root, "materials")
    if not os.path.isdir(material_dir):
        return False
    dest = os.path.join(output_dir, "materials")
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.copytree(material_dir, dest)
    return True


def validate_sprite_assignment(path):
    if not os.path.isfile(path):
        raise ValueError(f"Selected sprite file does not exist: {path}")
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".vtf", ".vmt"):
        raise ValueError("Sprite files must be game-ready .vtf or .vmt files.")


def copy_sprite_assignments(assignments, sprite_dir, output_dir):
    copied = []
    if not assignments:
        return copied
    sprite_dir = safe_game_path(sprite_dir, allow_empty=False)
    for _label, item in assignments.items():
        src = item.get("path") if isinstance(item, dict) else ""
        filename = item.get("filename") if isinstance(item, dict) else ""
        if not src:
            continue
        validate_sprite_assignment(src)
        if not filename or "/" in filename or "\\" in filename:
            raise ValueError("Sprite destination filename is invalid.")
        dest = os.path.join(output_dir, *sprite_dir.split("/"), filename)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(dest)
    return copied


def create_override_pack(options):
    name = str(options.get("name") or "").strip()
    if not name:
        raise ValueError("Pack name is required.")
    character = str(options.get("character") or "").strip() or "(unspecified)"
    source_target = options.get("source_target") or {}
    model_base = safe_game_path(source_target.get("model_base", ""), allow_empty=False, strip_ext=True)
    arms_base = safe_game_path(source_target.get("arms_base", ""), allow_empty=True, strip_ext=True)
    overrides_dir = options.get("overrides_dir") or OVERRIDES_DIR
    output_dir = os.path.join(overrides_dir, pack_folder_name(name))
    if os.path.exists(output_dir):
        raise FileExistsError(output_dir)
    os.makedirs(overrides_dir, exist_ok=True)
    try:
        os.makedirs(output_dir, exist_ok=False)
        old_cwd = os.getcwd()
        os.chdir(output_dir)
        try:
            copy_model_sidecars(options.get("main_model"), model_base)
            if options.get("arms_model") and arms_base:
                copy_model_sidecars(options.get("arms_model"), arms_base)
        finally:
            os.chdir(old_cwd)
        copy_material_root(options.get("material_root") or "", output_dir)
        copy_sprite_assignments(options.get("sprite_assignments") or {}, options.get("sprite_dir") or source_target.get("sprite_dir") or "", output_dir)
        meta = {
            "name": name,
            "character": character,
            "skin": str(options.get("skin") or "").strip(),
            "description": str(options.get("description") or "").strip(),
            "source_target": {
                "name": source_target.get("name") or character,
                "model_base": model_base,
                "arms_base": arms_base,
                "sprite_dir": safe_game_path(options.get("sprite_dir") or source_target.get("sprite_dir", ""), allow_empty=True),
            },
        }
        with open(os.path.join(output_dir, "override.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        return output_dir
    except Exception:
        if os.path.isdir(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)
        raise
```

- [ ] **Step 2: Run the targeted tests**

Run:

```powershell
python -m unittest tests.test_retargeting.RetargetingTests.test_create_override_pack_copies_models_materials_sprites_and_metadata tests.test_retargeting.RetargetingTests.test_create_override_pack_rejects_non_game_ready_sprite_files -v
```

Expected: both tests pass.

- [ ] **Step 3: Run the full test suite**

Run:

```powershell
python -m unittest discover -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

Run:

```powershell
git add override_manager.py tests/test_retargeting.py
git commit -m "Add local override pack builder"
```

---

### Task 3: Add the Override Maker UI

**Files:**
- Modify: `override_manager.py`

- [ ] **Step 1: Add an "Override Maker" button**

In `App._build`, add this next to the existing community/overrides buttons:

```python
        ttk.Button(bot, text="Override Maker", command=self.override_maker).pack(side="left", padx=4)
```

- [ ] **Step 2: Add the dialog method**

Add this method inside `class App` before `community_packs`:

```python
    def override_maker(self):
        win = tk.Toplevel(self)
        win.title("Override Maker")
        win.geometry("760x620")
        win.minsize(680, 520)
        win.transient(self)

        pack_name = tk.StringVar()
        skin = tk.StringVar(value="Local model + sprites")
        source_name = tk.StringVar(value="Himiko Yumeno")
        model_path = tk.StringVar()
        arms_path = tk.StringVar()
        material_root = tk.StringVar()
        sprite_dir = tk.StringVar()
        description = tk.StringVar(value="Created with Override Maker.")
        sprite_vars = {label: tk.StringVar() for label, _filename in SPRITE_SLOTS}
        status = tk.StringVar(value="")

        form = ttk.Frame(win, padding=10)
        form.pack(fill="both", expand=True)

        def row(label, var, browse=None):
            frame = ttk.Frame(form)
            frame.pack(fill="x", pady=3)
            ttk.Label(frame, text=label, width=18).pack(side="left")
            ttk.Entry(frame, textvariable=var).pack(side="left", fill="x", expand=True, padx=6)
            if browse:
                ttk.Button(frame, text="Browse", command=browse).pack(side="left")
            return frame

        def update_source(_event=None):
            target = find_target(self.cfg, source_name.get())
            if target:
                sprite_dir.set(target.get("sprite_dir", ""))

        def browse_model():
            path = filedialog.askopenfilename(parent=win, title="Select main .mdl", filetypes=[("Source model", "*.mdl")])
            if path:
                model_path.set(path)
                root = path
                while root and os.path.basename(root).lower() != "models":
                    parent = os.path.dirname(root)
                    if parent == root:
                        break
                    root = parent
                if os.path.basename(root).lower() == "models":
                    material_root.set(os.path.dirname(root))

        def browse_arms():
            path = filedialog.askopenfilename(parent=win, title="Select arms .mdl", filetypes=[("Source model", "*.mdl")])
            if path:
                arms_path.set(path)

        def browse_material_root():
            path = filedialog.askdirectory(parent=win, title="Select extracted addon folder with materials/")
            if path:
                material_root.set(path)

        row("Pack name", pack_name)
        row("Skin / variant", skin)

        source_frame = ttk.Frame(form)
        source_frame.pack(fill="x", pady=3)
        ttk.Label(source_frame, text="Source character", width=18).pack(side="left")
        source_combo = ttk.Combobox(source_frame, textvariable=source_name, state="readonly",
                                    values=[t["name"] for t in available_targets(self.cfg) if t["name"] != DEFAULT_TARGET_NAME])
        source_combo.pack(side="left", fill="x", expand=True, padx=6)
        source_combo.bind("<<ComboboxSelected>>", update_source)

        row("Main model", model_path, browse_model)
        row("Arms model", arms_path, browse_arms)
        row("Material root", material_root, browse_material_root)
        row("Sprite folder", sprite_dir)
        row("Description", description)

        sprite_box = ttk.LabelFrame(form, text="Manual sprite assignments")
        sprite_box.pack(fill="both", expand=True, pady=(10, 4))
        for label, filename in SPRITE_SLOTS:
            frame = ttk.Frame(sprite_box, padding=(6, 3))
            frame.pack(fill="x")
            ttk.Label(frame, text=f"{label} -> {filename}", width=28).pack(side="left")
            ttk.Entry(frame, textvariable=sprite_vars[label]).pack(side="left", fill="x", expand=True, padx=6)
            def choose(slot_label=label):
                path = filedialog.askopenfilename(parent=win, title=f"Select {slot_label} sprite", filetypes=[("Game sprite", "*.vtf *.vmt")])
                if path:
                    sprite_vars[slot_label].set(path)
            ttk.Button(frame, text="Pick", command=choose).pack(side="left")
            ttk.Button(frame, text="Clear", command=lambda slot_label=label: sprite_vars[slot_label].set("")).pack(side="left", padx=3)

        ttk.Label(form, textvariable=status, foreground="#a05").pack(fill="x", pady=(4, 0))

        def create():
            target = find_target(self.cfg, source_name.get())
            if not target:
                messagebox.showerror("Override Maker", "Select a source character.", parent=win)
                return
            assignments = {}
            for label, filename in SPRITE_SLOTS:
                path = sprite_vars[label].get().strip()
                if path:
                    assignments[label] = {"path": path, "filename": filename}
            output = os.path.join(OVERRIDES_DIR, pack_folder_name(pack_name.get()))
            if os.path.exists(output):
                if not messagebox.askyesno("Replace pack", f"Replace existing local override folder?\n\n{output}", parent=win):
                    return
                shutil.rmtree(output)
            try:
                created = create_override_pack({
                    "name": pack_name.get(),
                    "character": target["name"],
                    "skin": skin.get(),
                    "description": description.get(),
                    "source_target": target,
                    "main_model": model_path.get(),
                    "arms_model": arms_path.get(),
                    "material_root": material_root.get(),
                    "sprite_dir": sprite_dir.get(),
                    "sprite_assignments": assignments,
                })
            except Exception as e:
                status.set(str(e))
                messagebox.showerror("Override Maker", str(e), parent=win)
                return
            self.refresh()
            messagebox.showinfo("Override Maker", f"Created override pack:\n\n{created}", parent=win)
            win.destroy()

        buttons = ttk.Frame(win, padding=(10, 0, 10, 10))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Create Override", command=create).pack(side="right")
        ttk.Button(buttons, text="Cancel", command=win.destroy).pack(side="right", padx=6)

        update_source()
```

- [ ] **Step 3: Compile-check the app**

Run:

```powershell
python -m py_compile override_manager.py
```

Expected: command exits with status 0.

- [ ] **Step 4: Commit**

Run:

```powershell
git add override_manager.py
git commit -m "Add local override maker dialog"
```

---

### Task 4: Update Tutorial and Verify End-to-End

**Files:**
- Modify: `override_manager.py`
- Optionally modify: `README.md`

- [ ] **Step 1: Update tutorial text**

In `App.TUTORIAL`, change section 5 to mention both drag-and-drop packs and the new maker:

```python
        "5) ADD A NEW OVERRIDE\n"
        "   Click 'Override Maker' to build a pack from local model files\n"
        "   and manually assigned game-ready VTF/VMT sprites.\n"
        "   Or click 'Open overrides folder' and drop a pack FOLDER inside it,\n"
        "   then click Refresh. A pack looks like:\n"
```

- [ ] **Step 2: Run all verification**

Run:

```powershell
python -m unittest discover -v
python -m py_compile override_manager.py
```

Expected: tests pass and compile succeeds.

- [ ] **Step 3: Rebuild the portable exe if the repo already has its build command available**

Check the existing build workflow with:

```powershell
rg -n "pyinstaller|GMod Override Manager.exe|dist" README.md .github override_manager.py
```

If the command is present, run the same build command used by the repo and copy the rebuilt app to `C:\Users\user\Desktop\GMod_Override_Manager`.

- [ ] **Step 4: Commit documentation/build-related changes**

Run:

```powershell
git add override_manager.py README.md
git commit -m "Document override maker workflow"
```

Skip the commit if no files changed after Task 3.

---

## Self-Review

Spec coverage:

- New Override Maker button: Task 3.
- Maker dialog for metadata, model, arms, sprites: Task 3.
- Local source support: Task 2 and Task 3.
- Manual sprite category assignment: Task 3.
- Standard override folder creation: Task 2.
- `override.json` with `source_target`: Task 2.
- Main list refresh: Task 3.
- Workshop deferred: no implementation task, matching spec.
- Tests for pack-builder behavior: Task 1 and Task 2.

Placeholder scan: no `TBD`, `TODO`, or unspecified implementation steps remain.

Type consistency: the plan uses `create_override_pack(options)`, `SPRITE_SLOTS`, `copy_model_sidecars`, `copy_material_root`, and `copy_sprite_assignments` consistently across tests and UI.
