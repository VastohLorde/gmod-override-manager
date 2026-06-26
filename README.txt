GMOD OVERRIDE MANAGER
=====================

WHAT IT IS
A small app to manage model/skin overrides for Garry's Mod. Each override is a
folder ("pack") you drop into the "overrides" folder. The app lists them, shows
which character/skin each one replaces, and lets you turn each on or off.

HOW TO RUN
Double-click  "GMod Override Manager.exe"  (standalone - no Python needed).
(Source is included as override_manager.py if you'd rather run/edit it with
Python 3:  python "override_manager.py")

There's also a TUTORIAL button inside the app.

INCLUDED OVERRIDES
- Female Shuichi   (Shuichi Saihara -> female model + sprites)
- Israel Nekomaru  (Nekomaru Nidai -> Israel skin + sprites)

HOW TO ADD AN OVERRIDE
Drag a pack folder into the "overrides" folder next to this app, then hit
Refresh. A pack looks like:

  overrides/
    My Cool Skin/
      override.json        (optional info - see below)
      models/...           (the model files, same paths as the game)
      materials/...         (textures / sprites)

override.json (optional but recommended):
  {
    "name": "Female Shuichi",
    "character": "Shuichi Saihara",
    "skin": "Female model",
    "description": "what it does"
  }

ENABLE / DISABLE
Select a pack and click Enable or Disable (or double-click to toggle).
- Enable installs it as a LEGACY addon (addons/ovr_<name>). Legacy addons sit
  ABOVE the server's files, so the override wins even on servers you don't host.
- Disable removes it.

IMPORTANT
- Changes apply on the next map load / server reconnect - GMod can't hot-swap a
  model already loaded in your current session.
- This only changes what YOU see. Others need the same override enabled to see it.
- Needs the base addon for that character (e.g. the Danganronpa PlayerModels
  addon) for any shared textures.

SET YOUR GMOD FOLDER
If the app says it can't find 'addons', click Browse and pick your
  ...\steamapps\common\GarrysMod\garrysmod
folder, then Save.

SHARING
Zip this whole folder and send it. Whoever gets it runs the .bat and toggles
the overrides they want.
