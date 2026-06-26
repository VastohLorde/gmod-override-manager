# GMod Override Manager

A small Windows app to manage **model / skin overrides** for Garry's Mod.
Each override is a drop-in folder ("pack"); the app lists what character each one
replaces and lets you toggle them on/off.

## Download
Grab **`GMod_Override_Manager.zip`** from the [Releases](../../releases) page,
extract it anywhere, and run **`GMod Override Manager.exe`** (standalone — no
Python needed). There's a **Tutorial** button inside the app.

## How it works
Enabling a pack installs it as a **legacy addon** (`addons/ovr_<name>`). Legacy
addon files sit *above* the server's in GMod's load order, so the override wins
**even on servers you don't host** — something a Workshop subscription can't do.

> Changes apply on the next map load / server **reconnect** (GMod doesn't
> hot-swap a model already loaded in your current session). It only changes what
> **you** see — others need the same pack enabled.

## Adding a character override
Drop a pack folder into `overrides/`, then hit **Refresh**. A pack looks like:

```
overrides/
  My Override/
    override.json     # {name, character, skin, description}
    models/...        # model files (same paths as the game)
    materials/...     # textures / sprites
```

`override.json` example:

```json
{
  "name": "Female Shuichi",
  "character": "Shuichi Saihara",
  "skin": "Female model",
  "description": "Replaces Shuichi with the female model + sprites."
}
```

## Included packs
| Override | Character | Skin |
|---|---|---|
| Female Shuichi | Shuichi Saihara | Female model + sprites |
| Israel Nekomaru | Nekomaru Nidai | Israel skin + sprites |

## Notes
- Needs the base addon for that character (e.g. the Danganronpa PlayerModels
  addon) for any shared textures.
- The `.exe` is unsigned, so Windows SmartScreen may warn on first run
  ("More info → Run anyway"). You can also run the source: `python override_manager.py`.
