# Retargetable Overrides Design

## Goal

Override packs should be able to target any supported character from inside GMod Override Manager. A pack's baked target remains available as `Default`, but the user can choose another character from a list or enter a custom target for unusual cases.

Example: `Hoshino Himiko` can be selected, changed from `Default` to `Mukuro Ikusaba`, and enabled. Mukuro is only an example; the same workflow applies to any target in the character list. The manager installs Hoshino over the chosen character without requiring a duplicate local override folder.

## User Workflow

The main override list remains the starting point.

1. Select a local override pack.
2. Pick a target from a `Target Character` dropdown.
3. Click `Enable` or `Switch Target`.
4. Reconnect or change map in GMod.

The dropdown always includes:

- `Default`, meaning the pack's original baked target.
- Built-in Shinri Trial / Danganronpa character targets.
- `Custom target...`, for manual model, arms, and sprite paths.

Changing a pack from one target to another removes the previous installed addon for that pack, then installs the new target. `Disable` removes all installed targets for the selected pack.

## Target Data

The app owns a character target registry. Each target has:

```json
{
  "name": "Mukuro Ikusaba",
  "model_base": "models/dro/player/characters1/char16/char16",
  "arms_base": "models/dro/player/characters1/char16/c_arms/char16_arms",
  "sprite_dir": ""
}
```

`model_base` and `arms_base` omit the extension so the manager can map `.mdl`, `.dx90.vtx`, `.vvd`, and `.phy` consistently. `sprite_dir` is optional because not every character's courtroom sprite path is known locally.

The initial registry should include known model and arms paths from the local Danganronpa player model addon. Sprite paths can be added when known.

## Pack Source Target

Each pack needs a source target: the paths it was originally built to replace. The manager should infer this from the pack's files when possible:

- model base from the first playable model under `models/dro/player/...`
- arms base from a matching `c_arms` model
- sprite directory from the first `materials/dro/sprites/characters/...` folder

If inference fails, the pack still works for `Default`, but retargeting can show a clear error explaining which source path was missing.

Future packs may optionally declare this explicitly in `override.json`:

```json
{
  "source_target": {
    "model_base": "models/dro/player/characters3/char12/char12",
    "arms_base": "models/dro/player/characters3/char12/c_arms/char12_arms",
    "sprite_dir": "materials/dro/sprites/characters/dr_v3/himiko yumeno"
  }
}
```

## Install Behavior

The local pack folder is never modified.

When enabling `Default`, the manager copies the pack exactly as it does today.

When enabling a non-default target, the manager copies the pack into a generated addon folder and rewrites destination paths during copy:

- files matching the source model base are copied to the chosen target model base
- files matching the source arms base are copied to the chosen target arms base
- files under the source sprite directory are copied to the chosen target sprite directory, when both are known
- all unrelated files, such as Hoshino materials, are copied unchanged
- Lua files are copied unchanged for the first version unless a known source path appears as plain text; then simple text replacement may be applied conservatively

The generated addon slug should include both pack and target, for example:

```text
addons/ovr_hoshino_himiko__mukuro_ikusaba
```

This prevents collisions and makes cleanup predictable.

## Revert and Disable

`Default` is the revert path. Selecting `Default` and enabling removes the previous target-specific addon for that pack, then installs the original baked override.

`Disable` removes every installed addon whose slug belongs to the selected pack, including old target-specific addons. This avoids multiple targets for one pack staying active accidentally.

## Config

The manager stores the selected target per pack in `config.json`:

```json
{
  "pack_targets": {
    "ovr_hoshino_himiko": "Mukuro Ikusaba"
  },
  "custom_targets": {
    "My Custom Target": {
      "model_base": "...",
      "arms_base": "...",
      "sprite_dir": "..."
    }
  }
}
```

Existing config files remain valid. Missing `pack_targets` means every pack uses `Default`.

## Error Handling

The manager should block unsafe paths:

- absolute paths
- `..`
- paths outside `models/`, `materials/`, or `lua/`

If the selected target lacks a sprite path, model and arms retargeting can still proceed, but the UI should warn that sprites will stay on the pack's default character unless a custom sprite path is provided.

If retargeting fails, the partially generated addon folder is removed and the previous enabled state is not reported as changed.

## Testing

Manual verification should cover:

- existing `Default` enable/disable still works
- Hoshino can retarget from Himiko to another character model path
- switching target removes the old target addon
- disable removes all addons for the selected pack
- custom target rejects unsafe paths
- community pack install behavior is unchanged

Automated tests can cover the path mapping functions and config migration without requiring GMod.
