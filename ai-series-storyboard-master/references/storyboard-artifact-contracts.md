# AI 长剧分镜产物契约

## 目录

1. [共同规则](#共同规则)
2. [上游快照与选择性失效](#上游快照与选择性失效)
3. [场戏计划](#场戏计划)
4. [片段文件](#片段文件)
5. [Seedance 提示词](#seedance-提示词)
6. [版本与状态](#版本与状态)

## 共同规则

- 正式目录固定为 `STORYBOARD/EPxxx/SCxxx/`。
- 版本只允许 `vN.N` 或 `draft-v0.N`。
- 场次 ID 固定为 `EPddd-SCddd`；片段 ID 固定为 `EPddd-SCddd-SEGddd`。
- 正式提示词控制指令使用英文；只有登记过的源文本引号内允许原语言。
- 禁止 `latest`、`current`、未版本化文件或未登记 `@参考标签`。
- 不覆盖旧版。内容、上游引用或状态变化时写新版本。

```text
STORYBOARD/
└── EP001/SC001/
    ├── EP001-SC001-PLAN-v1.0.md
    ├── EP001-SC001-SEG001-v1.0.md
    └── EP001-SC001-SEG002-v1.0.md
```

## 上游快照与选择性失效

每份产物必须记录：

- `inherits-style`：创建时精确 STYLE-BASE。
- `asset-index-snapshot`：创建时精确 approved 索引。
- `asset-files`：本场实际使用的精确实体文件。
- `reference-calls`：本场实际使用的精确参考标签。

STYLE-BASE 版本变化时整场失效。索引升级时逐个比较本场 `asset-files` 与新 approved 索引：只有引用实体的当前文件或参考标签发生变化时，本场或对应片段失效；无关实体变化不构成失效。

`asset-files` 格式：

```text
CHAR-001=characters/CHAR-001-v1.0.md; CROWD-001=crowds/CROWD-001-v1.0.md; SCN-001=scenes/SCN-001-v1.0.md; PROP-001=props/PROP-001-v1.0.md
```

## 场戏计划

```markdown
## EP001-SC001-PLAN-v1.0｜林宅正厅 日 内
- inherits-style: STYLE-BASE-v1.0
- asset-index-snapshot: ASSET-INDEX-v1.1
- source: scripts/episode-001.md
- source-scene: EP001-SC001
- source-heading: 1-1 林宅正厅 日 内
- coverage: complete
- status: approved
- character-assets: CHAR-001, CHAR-002
- crowd-assets: CROWD-001
- scene-asset: SCN-001
- prop-assets: PROP-001
- asset-files: CHAR-001=characters/CHAR-001-v1.0.md; CHAR-002=characters/CHAR-002-v1.0.md; CROWD-001=crowds/CROWD-001-v1.0.md; SCN-001=scenes/SCN-001-v1.0.md; PROP-001=props/PROP-001-v1.0.md
- reference-calls: @CHAR-001-REF-v1.0, @CHAR-002-REF-v1.0, @CROWD-001-REF-v1.0, @SCN-001-REF-v1.0, @PROP-001-REF-v1.0
- segment-count: 2

### 场戏设计
1. 场戏叙事功能：
2. 核心戏剧目标：
3. 起始状态：
4. 结束状态：
5. 空间任务：
6. 连续性入口：
7. 连续性出口：

### Source Text Registry
~~~text
D001 | Dialogue | CHAR-001 | 原文台词
D002 | Voice-over | NARRATOR | 原文旁白
~~~

### Segment Catalog
| Segment ID | 时长 | 叙事功能 | 戏剧目标 | 角色资产 | 群众资产 | 场景资产 | 道具资产 | 原文 ID |
|---|---:|---|---|---|---|---|---|---|
| EP001-SC001-SEG001 | 8.0s | 建立对峙 | 迫使对方回应 | CHAR-001, CHAR-002 | CROWD-001 | SCN-001 | PROP-001 | D001 |
| EP001-SC001-SEG002 | 7.0s | 权力反转 | 暴露新线索 | CHAR-001, CHAR-002 | none | SCN-001 | PROP-001 | D002 |
```

没有台词、旁白或屏幕文字时，Source Text Registry 代码块只写 `none`，目录中的原文 ID 写 `none`。

## 片段文件

```markdown
## EP001-SC001-SEG001-v1.0｜迫使回应
- inherits-style: STYLE-BASE-v1.0
- asset-index-snapshot: ASSET-INDEX-v1.1
- inherits-plan: EP001-SC001-PLAN-v1.0
- source: scripts/episode-001.md
- source-scene: EP001-SC001
- coverage: complete
- status: approved
- duration: 8.0s
- character-assets: CHAR-001, CHAR-002
- crowd-assets: CROWD-001
- scene-asset: SCN-001
- prop-assets: PROP-001
- asset-files: CHAR-001=characters/CHAR-001-v1.0.md; CHAR-002=characters/CHAR-002-v1.0.md; CROWD-001=crowds/CROWD-001-v1.0.md; SCN-001=scenes/SCN-001-v1.0.md; PROP-001=props/PROP-001-v1.0.md
- reference-calls: @CHAR-001-REF-v1.0, @CHAR-002-REF-v1.0, @CROWD-001-REF-v1.0, @SCN-001-REF-v1.0, @PROP-001-REF-v1.0
- source-text-ids: D001

### 片段方案
1. 片段编号：
2. 片段名称：
3. 核心场景：
4. 登场主要角色：
5. 叙事功能：
6. 戏剧目标：
7. 情绪推进：
8. 关键动作：
9. 关键台词、旁白与屏幕文字：
10. 转场方式：
11. 与前后片段衔接：
12. 参考调用：

### Seedance 2.0 Prompt
~~~text
[FOUNDATION]
Duration: 8.0s
Frame: 16:9
References: @CHAR-001-REF-v1.0, @CHAR-002-REF-v1.0, @CROWD-001-REF-v1.0, @SCN-001-REF-v1.0, @PROP-001-REF-v1.0
Character CHAR-001: [Character Base 原文]
Character CHAR-002: [Character Base 原文]
Crowd CROWD-001: [Crowd Base 原文]
Scene SCN-001: [Scene Base 原文]
Prop PROP-001: [Prop Base 原文]

[ATMOSPHERE AND IMAGE QUALITY]
Style Core: [只从 STYLE-BASE 转译]
Visual Baseline: [只从 STYLE-BASE 转译]
Color and Tonality: [只从 STYLE-BASE 转译]

[VISUAL CONTENT]
Shot 1 [0.0s-3.0s]
Shot scale: ...
Composition: ...
Camera angle: ...
Camera movement: ...
Dramatic execution: The speaking character advances the immediate objective through one visible action, and the movement produces a medium-consistent change in pose, silhouette, facial design, breath, line, volume, surface, or distance. While that visible change remains active, the character delivers Dialogue [D001]: "原文台词" with a specified rhythm and volume; after the exact words, the listener reacts immediately and changes the final posture, eyeline, shape, or power distance held by the shot.

Shot 2 [3.0s-8.0s]
Shot scale: ...
Composition: ...
Camera angle: ...
Camera movement: ...
Dramatic execution: The subject begins from a precise pose and eyeline, performs one motivated action, and lets the action trigger a visible performance, line, deformation, volume, surface, or breathing change allowed by the inherited visual medium. Then the other person or the environment responds, leaving a specific final posture, distance, object state, silhouette, or gaze direction for the next shot.

Segment transition: ...
Continuity into next segment: ...
~~~
```

`character-assets`、`crowd-assets` 与 `prop-assets` 允许 `none`；`scene-asset` 永远必须存在。兼容旧产物时，缺少 `crowd-assets` 或 `prop-assets` 等同 `none`。`reference-calls` 和 `asset-files` 必须与实际使用集合完全一致。

## Seedance 提示词

- `[FOUNDATION]` 必须原样包含每个实际使用的 Character Base、Crowd Base、唯一 Scene Base 与 Prop Base，不得改词、压缩或混合。
- `[ATMOSPHERE AND IMAGE QUALITY]` 必须包含且只包含 `Style Core`、`Visual Baseline`、`Color and Tonality` 三项。
- `[VISUAL CONTENT]` 必须包含 2–4 个镜头；镜头编号连续，首镜从 0.0s 开始，相邻区间无空隙或重叠，尾镜结束时间等于片段时长。
- 每个镜头必须包含 `Shot scale`、`Composition`、`Camera angle`、`Camera movement` 与唯一一个 `Dramatic execution`；禁止出现旧字段 `Subject and action`、`Performance`。
- `Dramatic execution` 必须是单个连续英文段落，按时间顺序融合主体意图与动作、可见表演变化、关系对象的即时反应和镜头结束状态；不得把动作清单与情绪说明并排堆放。
- 原文调用只允许以内联形式嵌入 `Dramatic execution`：`Dialogue [Dxxx]: "..."`、`Voice-over [Dxxx]: "..."`、`On-screen text [Dxxx]: "..."`。引号内必须逐字等于 Source Text Registry，调用前后必须存在英文动作、说话方式或反应语句，禁止独立成行。
- Source Text Registry 中每个 ID 必须恰好分配给一个片段；不得遗漏或跨片段重复。
- 提示词末尾必须包含 `Segment transition` 与 `Continuity into next segment`。

## 版本与状态

- `coverage` 只允许 `complete` 或 `draft`。
- 新产物的 `status` 固定为 `approved`；`ready-for-review` 仅用于旧产物读取兼容。
- 同一场计划与其全部片段必须共享 STYLE-BASE、索引快照、coverage 和 status。
- 首次通过校验后直接交付 `approved` 计划与片段，不创建仅状态不同的副本，也不请求逐场审批。
- 只有用户明确提出镜头、文本分配、时长、资产引用或上游版本修改时才创建一个新的 `approved` 版本。
- 修改片段戏剧任务、镜头结构、源文本分配或引用资产时升级主版本；只压缩英文措辞且可见结果不变时升级次版本。
