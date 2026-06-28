import importlib
import json
import os
import shutil
import sys
import tempfile
import types
import unittest


sys.modules.setdefault("translate_cache", types.SimpleNamespace())
sys.modules.setdefault("live_translator", types.SimpleNamespace())
om = importlib.import_module("override_manager")


class RetargetingTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def write_file(self, rel, data=b"x"):
        path = os.path.join(self.tempdir, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        mode = "wb" if isinstance(data, bytes) else "w"
        kwargs = {} if isinstance(data, bytes) else {"encoding": "utf-8"}
        with open(path, mode, **kwargs) as f:
            f.write(data)
        return path

    def test_target_slug_and_addon_slug_include_target_for_non_default(self):
        pack = {"name": "Hoshino Himiko", "slug": "ovr_hoshino_himiko"}
        target = {"name": "Mukuro Ikusaba"}

        self.assertEqual("default", om.target_slug(om.DEFAULT_TARGET_NAME))
        self.assertEqual("mukuro_ikusaba", om.target_slug("Mukuro Ikusaba"))
        self.assertEqual("ovr_hoshino_himiko", om.addon_slug(pack, None))
        self.assertEqual("ovr_hoshino_himiko__mukuro_ikusaba", om.addon_slug(pack, target))

    def test_infer_source_target_from_pack_files(self):
        pack_dir = os.path.join(self.tempdir, "Hoshino Himiko")
        self.write_file("Hoshino Himiko/models/dro/player/characters3/char12/char12.mdl")
        self.write_file("Hoshino Himiko/models/dro/player/characters3/char12/char12.dx90.vtx")
        self.write_file("Hoshino Himiko/models/dro/player/characters3/char12/c_arms/char12_arms.mdl")
        self.write_file("Hoshino Himiko/materials/dro/sprites/characters/dr_v3/himiko yumeno/ct_sprite_1.vtf")

        source = om.infer_source_target(pack_dir)

        self.assertEqual("models/dro/player/characters3/char12/char12", source["model_base"])
        self.assertEqual("models/dro/player/characters3/char12/c_arms/char12_arms", source["arms_base"])
        self.assertEqual("materials/dro/sprites/characters/dr_v3/himiko yumeno", source["sprite_dir"])

    def test_infer_source_target_prefers_override_json(self):
        pack_dir = os.path.join(self.tempdir, "Pack")
        os.makedirs(pack_dir, exist_ok=True)
        with open(os.path.join(pack_dir, "override.json"), "w", encoding="utf-8") as f:
            json.dump({
                "source_target": {
                    "model_base": "models/dro/player/characters3/char12/char12.mdl",
                    "arms_base": "models/dro/player/characters3/char12/c_arms/char12_arms.mdl",
                    "sprite_dir": "materials/dro/sprites/characters/dr_v3/himiko yumeno/"
                }
            }, f)

        source = om.infer_source_target(pack_dir)

        self.assertEqual("models/dro/player/characters3/char12/char12", source["model_base"])
        self.assertEqual("models/dro/player/characters3/char12/c_arms/char12_arms", source["arms_base"])
        self.assertEqual("materials/dro/sprites/characters/dr_v3/himiko yumeno", source["sprite_dir"])

    def test_retarget_path_maps_model_arms_and_sprite_paths(self):
        source = {
            "model_base": "models/dro/player/characters3/char12/char12",
            "arms_base": "models/dro/player/characters3/char12/c_arms/char12_arms",
            "sprite_dir": "materials/dro/sprites/characters/dr_v3/himiko yumeno",
        }
        target = {
            "name": "Mukuro Ikusaba",
            "model_base": "models/dro/player/characters1/char16/char16",
            "arms_base": "models/dro/player/characters1/char16/c_arms/char16_arms",
            "sprite_dir": "materials/dro/sprites/characters/dr_1/mukuro ikusaba",
        }

        self.assertEqual(
            "models/dro/player/characters1/char16/char16.mdl",
            om.map_retarget_path("models/dro/player/characters3/char12/char12.mdl", source, target),
        )
        self.assertEqual(
            "models/dro/player/characters1/char16/c_arms/char16_arms.dx90.vtx",
            om.map_retarget_path("models/dro/player/characters3/char12/c_arms/char12_arms.dx90.vtx", source, target),
        )
        self.assertEqual(
            "materials/dro/sprites/characters/dr_1/mukuro ikusaba/ct_sprite_1.vtf",
            om.map_retarget_path("materials/dro/sprites/characters/dr_v3/himiko yumeno/ct_sprite_1.vtf", source, target),
        )
        self.assertEqual(
            "materials/models/hoshino_new/hair.vmt",
            om.map_retarget_path("materials/models/hoshino_new/hair.vmt", source, target),
        )

    def test_retarget_path_leaves_sprites_when_target_sprite_missing(self):
        source = {
            "model_base": "models/dro/player/characters3/char12/char12",
            "arms_base": "models/dro/player/characters3/char12/c_arms/char12_arms",
            "sprite_dir": "materials/dro/sprites/characters/dr_v3/himiko yumeno",
        }
        target = {
            "name": "Mukuro Ikusaba",
            "model_base": "models/dro/player/characters1/char16/char16",
            "arms_base": "models/dro/player/characters1/char16/c_arms/char16_arms",
            "sprite_dir": "",
        }

        self.assertEqual(
            "materials/dro/sprites/characters/dr_v3/himiko yumeno/ct_sprite_1.vtf",
            om.map_retarget_path("materials/dro/sprites/characters/dr_v3/himiko yumeno/ct_sprite_1.vtf", source, target),
        )

    def test_safe_game_path_rejects_unsafe_paths(self):
        self.assertEqual("models/dro/player/characters1/char16/char16", om.safe_game_path("models\\dro\\player\\characters1\\char16\\char16.mdl", allow_empty=False, strip_ext=True))
        for value in ("", "../models/x", "/models/x", "C:/models/x", "cfg/client.vdf"):
            with self.assertRaises(ValueError):
                om.safe_game_path(value, allow_empty=False)

    def test_installed_pack_addons_uses_pack_prefix_only(self):
        addons = os.path.join(self.tempdir, "addons")
        os.makedirs(os.path.join(addons, "ovr_hoshino_himiko"), exist_ok=True)
        os.makedirs(os.path.join(addons, "ovr_hoshino_himiko__mukuro_ikusaba"), exist_ok=True)
        os.makedirs(os.path.join(addons, "ovr_hoshino_himiko_extra"), exist_ok=True)
        os.makedirs(os.path.join(addons, "ovr_other_pack"), exist_ok=True)
        cfg = {"gmod_path": self.tempdir}
        pack = {"name": "Hoshino Himiko", "slug": "ovr_hoshino_himiko"}

        found = sorted(os.path.basename(p) for p in om.installed_pack_addons(cfg, pack))

        self.assertEqual(["ovr_hoshino_himiko", "ovr_hoshino_himiko__mukuro_ikusaba"], found)

    def test_enable_retarget_copies_to_target_specific_addon(self):
        pack_dir = os.path.join(self.tempdir, "Hoshino Himiko")
        self.write_file("Hoshino Himiko/models/dro/player/characters3/char12/char12.mdl", b"model")
        self.write_file("Hoshino Himiko/models/dro/player/characters3/char12/char12.dx90.vtx", b"vtx")
        self.write_file("Hoshino Himiko/models/dro/player/characters3/char12/c_arms/char12_arms.mdl", b"arms")
        self.write_file("Hoshino Himiko/materials/dro/sprites/characters/dr_v3/himiko yumeno/ct_sprite_1.vtf", b"sprite")
        self.write_file("Hoshino Himiko/materials/models/hoshino_new/hair.vtf", b"material")
        with open(os.path.join(pack_dir, "addon.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "Hoshino Himiko"}, f)
        cfg = {"gmod_path": self.tempdir}
        pack = {"name": "Hoshino Himiko", "slug": "ovr_hoshino_himiko", "folder": pack_dir}
        target = {
            "name": "Mukuro Ikusaba",
            "model_base": "models/dro/player/characters1/char16/char16",
            "arms_base": "models/dro/player/characters1/char16/c_arms/char16_arms",
            "sprite_dir": "materials/dro/sprites/characters/dr_1/mukuro ikusaba",
        }

        om.enable(cfg, pack, target)

        addon = os.path.join(self.tempdir, "addons", "ovr_hoshino_himiko__mukuro_ikusaba")
        self.assertTrue(os.path.exists(os.path.join(addon, "models/dro/player/characters1/char16/char16.mdl")))
        self.assertTrue(os.path.exists(os.path.join(addon, "models/dro/player/characters1/char16/c_arms/char16_arms.mdl")))
        self.assertTrue(os.path.exists(os.path.join(addon, "materials/dro/sprites/characters/dr_1/mukuro ikusaba/ct_sprite_1.vtf")))
        self.assertTrue(os.path.exists(os.path.join(addon, "materials/models/hoshino_new/hair.vtf")))
        self.assertFalse(os.path.exists(os.path.join(self.tempdir, "addons", "ovr_hoshino_himiko")))

    def test_disable_removes_default_and_retargeted_addons_for_pack(self):
        addons = os.path.join(self.tempdir, "addons")
        os.makedirs(os.path.join(addons, "ovr_hoshino_himiko"), exist_ok=True)
        os.makedirs(os.path.join(addons, "ovr_hoshino_himiko__mukuro_ikusaba"), exist_ok=True)
        os.makedirs(os.path.join(addons, "ovr_other_pack"), exist_ok=True)
        cfg = {"gmod_path": self.tempdir}
        pack = {"name": "Hoshino Himiko", "slug": "ovr_hoshino_himiko"}

        om.disable(cfg, pack)

        self.assertFalse(os.path.exists(os.path.join(addons, "ovr_hoshino_himiko")))
        self.assertFalse(os.path.exists(os.path.join(addons, "ovr_hoshino_himiko__mukuro_ikusaba")))
        self.assertTrue(os.path.exists(os.path.join(addons, "ovr_other_pack")))


if __name__ == "__main__":
    unittest.main()
