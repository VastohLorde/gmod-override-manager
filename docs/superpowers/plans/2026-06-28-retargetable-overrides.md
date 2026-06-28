# Retargetable Overrides Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `Default` plus character-list target selector so any override pack can be enabled over another supported character from inside GMod Override Manager.

**Architecture:** Keep local packs unchanged. Add pure helper functions for target inference, path validation, retarget copy mapping, and target-specific addon cleanup; then wire those helpers into the existing Tkinter UI.

**Tech Stack:** Python 3 standard library, Tkinter, `unittest`, existing legacy GMod addon folder copy behavior.

---

### Task 1: Retarget Helpers And Tests

**Files:**
- Modify: `override_manager.py`
- Create: `tests/test_retargeting.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_retargeting.py` with tests for slug generation, source inference, model/arms/sprite path mapping, unsafe path rejection, and target addon cleanup prefix selection.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m unittest tests.test_retargeting -v`
Expected: failures for missing helper functions.

- [ ] **Step 3: Implement helpers**

In `override_manager.py`, add:
- `DEFAULT_TARGET_NAME`
- `CHARACTER_TARGETS`
- `safe_game_path`
- `normalize_game_path`
- `path_without_ext`
- `infer_source_target`
- `target_key`
- `target_slug`
- `addon_slug`
- `pack_addon_prefix`
- `installed_pack_addons`
- `disable_all_pack_targets`
- `map_retarget_path`
- `copy_pack_tree`

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m unittest tests.test_retargeting -v`
Expected: all tests pass.

### Task 2: Enable/Disable Retargeting

**Files:**
- Modify: `override_manager.py`
- Modify: `tests/test_retargeting.py`

- [ ] **Step 1: Add tests for enabled target folders**

Extend tests so enabling a target copies files to a target-specific addon slug and disabling removes all target add-ons for the pack.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m unittest tests.test_retargeting -v`
Expected: target enable/disable tests fail before implementation.

- [ ] **Step 3: Update enable/disable functions**

Change `is_enabled`, `enable`, and `disable` to accept an optional target. `Default` preserves current behavior; non-default uses retarget copy and target-specific slug.

- [ ] **Step 4: Run tests to verify pass**

Run: `python -m unittest tests.test_retargeting -v`
Expected: all tests pass.

### Task 3: UI Target Selector

**Files:**
- Modify: `override_manager.py`

- [ ] **Step 1: Add target selector UI**

Add a `Target Character` dropdown above the buttons. Populate it with `Default`, built-in character targets, and `Custom target...`.

- [ ] **Step 2: Add custom target dialog**

When `Custom target...` is selected, prompt for model base, arms base, and optional sprite folder. Validate with `safe_game_path` and save the custom target in `config.json`.

- [ ] **Step 3: Persist pack target selection**

Save the selected target per pack slug under `pack_targets`. Refresh and selection changes should restore the saved value.

- [ ] **Step 4: Wire buttons**

`Enable` should install the selected target. `Disable` should remove every installed addon for the selected pack. The status column should show `ENABLED: Default` or `ENABLED: <target>` when an installed target is found.

### Task 4: Docs And Verification

**Files:**
- Modify: `README.md`
- Modify: `override_manager.py`

- [ ] **Step 1: Update tutorial and README**

Document selecting a target, reverting by choosing `Default`, and using custom target paths.

- [ ] **Step 2: Run verification**

Run:
- `python -m unittest discover -v`
- `python -m py_compile override_manager.py`

Expected: both commands exit 0.

- [ ] **Step 3: Commit**

Commit code, tests, and docs with message `Add retargetable override installs`.
