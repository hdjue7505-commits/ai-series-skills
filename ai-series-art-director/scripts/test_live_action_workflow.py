"""Focused gate and text-handoff regression; no image or storyboard generation."""

from pathlib import Path
import runpy
import tempfile
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = SKILL_ROOT.parent
ART = runpy.run_path(str(SKILL_ROOT / "scripts" / "validate_artifacts.py"))
DNA = runpy.run_path(str(SKILLS_ROOT / "ai-series-visual-dna/scripts/validate_artifacts.py"))
STORYBOARD = runpy.run_path(
    str(SKILLS_ROOT / "ai-series-storyboard-master/scripts/validate_storyboards.py")
)

STYLE = (
    "Visual ontology: live-action fantasy cinema with integrated cinematic VFX, 16:9. "
    "World and period: a cultivation world where levitation and spiritual light are established; "
    "their visual expression preserves wonder without adding new abilities. "
    "Production design: suspended architecture and layered ceremonial garments share coherent "
    "scale, construction language and readable silhouettes. "
    "Color system: jade and ivory materials support luminous violet energy accents. "
    "Lighting system: daylight and spiritual emitters retain clear hierarchy, consistent "
    "occlusion and motivated reflected light, including during powerful manifestations. "
    "Imaging base: contemporary digital cinema response, natural skin separation, controlled "
    "highlights and resolved dark detail without compulsory grain or vintage decay. "
    "Lens family: moderate wide through portrait lenses preserve spatial relationships. "
    "Human rendering: human figures retain living skin and anatomy; spirits preserve "
    "established translucency without becoming plastic figures. "
    "Material logic: silk, stone, metal and spiritual substances retain distinct reflection "
    "and transparency rules; levitation does not require mechanical support. "
    "Staging tendency: human relationships remain readable in quiet settings and grand "
    "supernatural spaces. Global exclusions: no plastic skin, no game key art, no advertising "
    "poses, no removal of established supernatural traits to simulate realism."
)

# These are test design choices, not an existing project's canon or released assets.
CASES = (
    {
        "prefix": "CHAR", "folder": "characters", "kind": "character", "name": "灵体守门人",
        "heading": "主要角色", "base_heading": "Character Base",
        "model_heading": "Character Model-Sheet Prompt", "validator": "validate_character",
        "fields": (
            "角色定位", "叙事作用", "核心识别点", "年龄与外貌", "发型", "服装", "配色",
            "配饰、武器与道具", "气质关键词", "连续性锚点",
        ),
        "model": (
            "Live-action fantasy costume and spirit model sheet with integrated cinematic VFX, "
            "16:9, pure white background. The upper-left panel shows the same adult face with "
            "natural anatomical structure; the lower-left panel resolves luminous violet wrist "
            "markings and translucent sleeve edges. On the right side, front view, profile view "
            "and back view retain the same ivory robe, long black hair and jade clasp. Continuity "
            "anchors remain visible through controlled edge contrast against white. Preserve the "
            "spirit's intrinsic translucency without adding an environment, attack pose or opaque "
            "skin substitute. Daylight response and local energy reflections inherit the selected "
            "world rules; garment texture remains distinct from spiritual radiance."
        ),
        "base": (
            "An adult guardian spirit with a narrow face, dark eyes and long black hair secured "
            "by a jade clasp. An ivory layered robe covers a translucent body. Violet wrist "
            "markings remain visible through the sleeves. The robe silhouette, clasp shape and "
            "translucency are stable identifying traits."
        ),
        "trait": "translucent body",
    },
    {
        "prefix": "CROWD", "folder": "crowds", "kind": "crowd", "name": "宗门值守者",
        "heading": "群众演员", "base_heading": "Crowd Base",
        "model_heading": "Crowd Model-Sheet Prompt", "validator": "validate_crowd",
        "fields": (
            "群体定位", "叙事与空间作用", "组织与层级构成", "人口构成与差异范围",
            "体态与面貌分布", "发型与妆容系统", "服装与制服层级", "配色、配饰与携带物",
            "职业姿态与动作语汇", "连续性锚点与允许变化",
        ),
        "model": (
            "Live-action fantasy wardrobe system, 16:9, pure white background, group lineup "
            "with no duplicated faces. Show established rank variations through collar height "
            "and jade fastening shapes, with front view, profile view and back view resolving "
            "each uniform structure. Continuity anchors are ivory woven robes, dark green sashes "
            "and intrinsic violet collar markings realized through integrated cinematic VFX. "
            "Representative adults differ in age, height, facial anatomy and hair arrangement "
            "while sharing one order's visual identity. Preserve living skin and distinct textile "
            "reflection. The neutral identification stance establishes clothing rather than a "
            "fixed dramatic formation, and the luminous markings must remain legible without "
            "washing out cloth edges or changing the white identification background."
        ),
        "base": (
            "Adult members of a gatekeeping order vary in age, height and facial structure. "
            "They wear ivory woven robes, dark green sashes and jade collar fastenings. "
            "Violet collar markings emit a stable intrinsic light. Senior members have taller "
            "collars, while hair arrangements vary within the same restrained grooming system. "
            "Shared clothing and markings remain stable across individual differences."
        ),
        "trait": "stable intrinsic light",
    },
    {
        "prefix": "SCN", "folder": "scenes", "kind": "scene", "name": "悬浮山门",
        "heading": "核心场景", "base_heading": "Scene Base",
        "model_heading": "Scene Model-Sheet Prompt", "validator": "validate_scene",
        "fields": (
            "场景名称", "场景作用", "空间类型", "时代与世界观属性", "全景布局结构",
            "主视觉焦点", "关键道具", "色彩氛围", "光线逻辑", "可调度区域", "角色可站位区域",
            "连续性锚点",
        ),
        "model": (
            "Live-action fantasy environment with integrated cinematic VFX, 16:9, 2x2 four-panel "
            "grid of the same scene. A full-scene overview establishes foreground landing steps, "
            "midground suspended court and background stone arch. A non-wide feature-focused "
            "panel resolves the defining scene features: unsupported platform edges and their "
            "violet inscriptions. Complementary panels preserve identical platform spacing, "
            "entrance bridge, exit portal, key props and light source positions. Daylight and "
            "spiritual inscriptions produce consistent illumination across every panel. Blocking "
            "zones and standing positions remain readable on the upper surfaces. Preserve "
            "the floating architecture without adding support columns or replacing the "
            "mountain void with ordinary ground; feature details retain identifiable spatial "
            "relationships to the overview."
        ),
        "base": (
            "A stone gate complex consists of three floating platforms at fixed relative "
            "heights above an open mountain void. Landing steps lead to a central court; "
            "a jade bridge forms the entrance and a stone portal marks the exit. Violet "
            "inscriptions line the platform rims. Upper surfaces provide clear standing areas "
            "and connected routes without support columns."
        ),
        "trait": "three floating platforms",
    },
    {
        "prefix": "PROP", "folder": "props", "kind": "prop", "name": "御剑法器",
        "heading": "重要道具", "base_heading": "Prop Base",
        "model_heading": "Prop Model-Sheet Prompt", "validator": "validate_prop",
        "fields": (
            "道具名称", "道具类别", "叙事功能", "归属与流转", "尺寸与人体尺度",
            "轮廓与核心识别点", "结构与构造", "材料与制造工艺", "配色与表面状态",
            "使用、握持与佩戴逻辑", "状态谱系与变化触发", "连续性锚点",
        ),
        "model": (
            "Live-action fantasy prop identification board with integrated cinematic VFX, "
            "16:9, neutral background. Show a three-quarter view alongside front view, profile "
            "view, back view and top view of one jade-edged sword. A hand silhouette provides "
            "scale reference without prescribing a current holder. Material details resolve "
            "the silver core, jade edges and violet channel; continuity anchors include the "
            "notched guard and tapered tip. Show only established inactive and spiritually "
            "activated states. Activation permits unsupported levitation and a violet channel "
            "emission; do not invent motors or change the sword into a handheld-only weapon. "
            "Maintain legible silhouette, coherent reflections and identical dimensions in "
            "all views without decorative commercial lighting."
        ),
        "base": (
            "A ninety-centimeter sword has a silver core, jade edges, a notched guard and "
            "a narrow violet channel. Its initial inactive state is unlit. Spiritual activation "
            "allows unsupported levitation and channel emission without motors or physical "
            "grips. The tapered tip, guard notch and material boundaries remain identical "
            "in both permitted states."
        ),
        "trait": "unsupported levitation",
    },
)


class LiveActionWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="live-action-workflow-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.style_path = self.root / "DNA/STYLE-BASE-v1.0.md"
        self.style_path.parent.mkdir()

    def write_style(self, body):
        self.style_path.write_text(
            f"## STYLE-BASE-v1.0\n\n~~~text\n{body}\n~~~\n", encoding="utf-8"
        )
        return self.style_path

    def test_live_action_and_film_effects_are_accepted(self):
        for ontology in (
            "live-action cinema",
            "live-action fantasy with integrated cinematic VFX",
            "live-action cinema with CGI creatures and digital environments",
            "live-action cinema; no animation; no 2D; no 3D animation",
        ):
            with self.subTest(ontology=ontology):
                self.write_style(f"Visual ontology: {ontology}, 16:9. World and period: fantasy.")
                self.assertEqual(
                    ART["validate_style_file"](self.style_path),
                    ("STYLE-BASE-v1.0", frozenset({"live-action"})),
                )

    def test_animation_and_ambiguous_medium_labels_are_rejected(self):
        for ontology in (
            "2D animation", "3D animation", "motion-comic", "stop-motion",
            "live-action with mixed-media animation", "live-action and 2D animation",
            "live-action cinema with 3D VFX",
        ):
            with self.subTest(ontology=ontology):
                self.write_style(f"Visual ontology: {ontology}, 16:9. World and period: fantasy.")
                with self.assertRaisesRegex(ValueError, "requires a live-action-only"):
                    ART["validate_style_file"](self.style_path)

    def test_entity_cannot_switch_to_animation(self):
        result = ART["Result"](self.root / "CHAR-001-v1.0.md", "CHARACTER")
        ART["require_style_ontology"](
            result, "model", "live-action with 2D animation", frozenset({"live-action"})
        )
        self.assertTrue(any("unsupported visual ontology" in error for error in result.errors))

    def test_fantasy_asset_handoff_preserves_all_four_bases(self):
        self.write_style(STYLE)
        self.assertEqual(DNA["validate_style"](self.style_path).errors, [])
        style_id, traits = ART["validate_style_file"](self.style_path)
        art_root = self.root / "ART"
        art_root.mkdir()
        index_path = art_root / "ASSET-INDEX-v1.0.md"
        index = (
            "## ASSET-INDEX-v1.0\n- inherits-style: STYLE-BASE-v1.0\n"
            "- source: synthetic-test-only\n- coverage: draft\n- status: approved\n\n"
        )
        for case in CASES:
            asset_id = f"{case['prefix']}-001"
            path = art_root / case["folder"] / f"{asset_id}-v1.0.md"
            path.parent.mkdir()
            label = f"@{asset_id}-REF-v1.0"
            plan = "\n".join(
                f"{n}. {field}：design-choice，仅为本测试建立的可见设计，不属项目正史。"
                for n, field in enumerate(case["fields"], 1)
            )
            raw = (
                f"## {asset_id}-v1.0｜{case['name']}\n"
                f"- inherits-style: {style_id}\n- inherits-index: ASSET-INDEX-v1.0\n"
                f"- source: synthetic-test-only\n- coverage: draft\n"
                f"- reference-label: {label}\n- reference-image: pending\n\n"
                f"### 建模方案\n{plan}\n\n### {case['model_heading']}\n~~~text\n"
                f"{case['model']}\n~~~\n\n### {case['base_heading']}\n~~~text\n"
                f"{case['base']}\n~~~\n"
            )
            path.write_text(raw, encoding="utf-8")
            with self.subTest(asset=asset_id):
                result = ART[case["validator"]](path, raw, style_id, "ASSET-INDEX-v1.0", traits)
                self.assertEqual(result.errors, [])
            index += (
                f"### {case['heading']}\n"
                "| Asset ID | 名称 | 收录依据 | 出现范围 | 当前文件 | 参考标签 |\n"
                "|---|---|---|---|---|---|\n"
                f"| {asset_id} | {case['name']} | 测试连续性 | TEST | "
                f"{case['folder']}/{path.name} | {label} |\n\n"
            )
        index = index.rstrip() + "\n"
        index_path.write_text(index, encoding="utf-8")
        self.assertEqual(ART["validate_index"](index_path, index, style_id).errors, [])
        for extra_newline in ("\n", "\r\n"):
            with self.subTest(trailing_blank_line=repr(extra_newline)):
                invalid = ART["validate_index"](index_path, index + extra_newline, style_id)
                self.assertTrue(any("trailing blank lines" in error for error in invalid.errors))
        self.assertEqual(ART["validate_index_file"](index_path), "ASSET-INDEX-v1.0")
        downstream_id, _, downstream_traits = STORYBOARD["validate_style"](self.style_path)
        self.assertEqual((downstream_id, downstream_traits), (style_id, traits))
        index_id, assets = STORYBOARD["load_approved_index"](index_path, style_id)
        self.assertEqual(index_id, "ASSET-INDEX-v1.0")
        self.assertEqual(set(assets), {f"{case['prefix']}-001" for case in CASES})
        for case in CASES:
            asset = assets[f"{case['prefix']}-001"]
            self.assertEqual(asset.base, case["base"])
            self.assertIn(case["trait"], asset.base)


if __name__ == "__main__":
    unittest.main()
