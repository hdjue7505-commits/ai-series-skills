# AI Series Skills Bundle

This directory packages four complementary Codex skills for AI series production:

- `manga-screenwriter` — develops story seeds or source material into a file-managed Chinese series screenplay, including series structure, episode outlines, script batches, continuity records, and evidence-based review.
- `ai-series-visual-dna` — establishes and validates the live-action cinematic `STYLE-BASE` from the screenplay and confirmed story materials.
- `ai-series-art-director` — builds the approved continuity asset index and entity bases.
- `ai-series-storyboard-master` — turns one approved scene into validated storyboard segments (up to 30 seconds, 6–12 shots) and source-bound, silent, caption-free Blender whitebox previs using all relevant asset reference images. Seedance submission limits are checked separately.

Each skill is self-contained and includes its `SKILL.md`, agent metadata, and references, with templates or validation scripts where applicable. The intended handoff order is:

```text
manga-screenwriter → ai-series-visual-dna → ai-series-art-director → ai-series-storyboard-master
```

Start with `manga-screenwriter` when developing a new story. For the visual DNA stage, hand off the current project record, confirmed premise and character/world settings, series structure, episode outlines, available screenplay, and review status with their exact versions and coverage. Existing suitable story materials can enter directly at the visual DNA stage. Incomplete materials remain draft inputs, not a completed series.

The downstream visual pipeline is live-action cinematic. Confirm that visual direction before entering `ai-series-visual-dna`; an animation project must use a compatible animation workflow instead. Screenwriting does not create or approve `STYLE-BASE`, and handing off story materials does not approve the downstream visual design.
