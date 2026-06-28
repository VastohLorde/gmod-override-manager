# Override Maker Design

## Goal

Add an Override Maker to GMod Override Manager so users can create new override packs without manually assembling folder paths and metadata. The first implementation is local-first: it builds a normal local override pack from selected local model files/folders and manually assigned sprite files. Steam Workshop link downloading is deferred to a later version.

The generated pack must behave like every existing pack: it appears in the main list, can be enabled or disabled, can be retargeted through Target Character, and can later be zipped for community pack submission.

## Scope

Included in the first version:

- A new "Override Maker" button in the main window.
- A maker dialog for pack metadata, source character, model files, optional arms, and sprites.
- Local source support for an extracted addon folder or direct model file selection.
- Manual sprite category assignment by the user.
- Creation of a standard override folder under `overrides/`.
- Writing `override.json`, including `source_target` when the user selects a known source character.
- Refreshing the main pack list after successful creation.

Not included in the first version:

- Automatic Steam Workshop download by URL.
- Automatic `.gma` extraction.
- Automatic sprite category detection.
- Sprite image conversion from PNG/JPG to VTF. The first version only accepts game-ready VTF/VMT assets.
- Bodygroup repair beyond the existing retarget install behavior.

## User Flow

The user clicks "Override Maker" from the main window.

The dialog asks for:

- Pack name.
- Character/source character, using the same character list as the Target Character dropdown.
- Skin/variant text.
- Description.
- Model source folder or main `.mdl` file.
- Optional arms `.mdl` file.
- Sprite assignments.

Sprites are assigned manually because the manager cannot reliably infer meaning from arbitrary sprite names. The dialog should offer rows for common Shinri Trial sprite slots such as normal talk sprites, argue sprites, consent/special sprites, and scrum debate sprites. Each row lets the user choose a file, clear it, and see whether it is assigned.

When the user clicks Create, the manager validates required fields, creates a sanitized folder under `overrides/`, copies selected model-related files and materials, copies selected sprites into the selected source character's sprite path, and writes metadata.

## Model Copying

For local model input, the maker copies files conservatively:

- If the user selects a main `.mdl`, copy the model sidecar files with the same base name from the same folder, including `.mdl`, `.vvd`, `.phy`, `.dx90.vtx`, `.sw.vtx`, and `.ani` when present.
- If the user selects an arms `.mdl`, copy the same sidecar set for the arms model.
- If the user selects an extracted addon folder, use it as the material root for referenced materials and allow the main model to be picked from inside it.
- Copy `materials/` from the selected extracted addon folder when present. This is blunt but reliable for local-first creation.

The first version does not parse `.mdl` material references. That can be added later if pack size becomes a problem.

## Sprite Copying

Sprite assignment is explicit. The maker does not guess categories from filenames.

The source character determines the destination sprite folder when it is known. For example, selecting Himiko uses that target's configured sprite directory. If the selected character has no known sprite folder, the user can enter a custom sprite directory.

The maker copies assigned sprite files into the destination sprite folder using the destination filename for that category. The UI must make it clear that files should already be game-ready sprite assets, usually `.vtf` and matching `.vmt` when needed. If a user selects `.png` or `.jpg`, the first version should reject it with a clear error instead of silently producing a broken pack.

## Metadata

The generated `override.json` contains:

```json
{
  "name": "Example Override",
  "character": "Himiko Yumeno",
  "skin": "Example model + sprites",
  "description": "Created with Override Maker.",
  "source_target": {
    "name": "Himiko Yumeno",
    "model_base": "models/dro/player/characters3/char12/char12",
    "arms_base": "models/dro/player/characters3/char12/c_arms/char12_arms",
    "sprite_dir": "materials/dro/sprites/characters/dr_v3/himiko yumeno"
  }
}
```

`source_target` is important because existing retargeting depends on knowing the pack's original baked model and sprite paths.

## Error Handling

The dialog should block creation and show a direct error when:

- Pack name is empty.
- The destination pack folder already exists, unless the user confirms replacement.
- No main model is selected.
- The selected model file does not exist.
- The selected source character has no sprite directory and the user has assigned sprites without entering a custom sprite directory.
- A selected sprite file is not `.vtf` or `.vmt`.

If copying fails halfway through, the partially created output folder should be removed.

## Future Workshop Support

Workshop link support is planned as a second version. It should add a source mode where the user pastes a Workshop URL or item ID. The manager will then download/extract the item and pass the extracted folder into the same local maker pipeline.

That later version should handle:

- SteamCMD path detection or configuration.
- `gmad.exe` detection from the configured GMod install.
- Workshop item download.
- `.gma` extraction.
- Model selection from the extracted folder.
- Clear errors when dependencies are missing.

Keeping Workshop as a layer over the local maker avoids duplicating pack creation logic.

## Testing

Add unit tests for the non-UI creation pipeline:

- Pack folder names are sanitized.
- Main model sidecars are copied to the selected source character model path.
- Arms sidecars are copied when selected.
- Assigned sprite files are copied to the expected sprite filenames.
- `override.json` includes source metadata.
- Invalid sprite extensions are rejected.
- Failed creation cleans up partial output.

Manual UI verification should cover opening the dialog, selecting local files, creating a pack, seeing it appear in the main list, and enabling it.
