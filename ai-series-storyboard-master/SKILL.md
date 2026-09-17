---
name: ai-series-storyboard-master
description: >-
  按已确认 STYLE-BASE 的实际视觉本体，把 AI 长剧、动画或漫剧的一场戏拆成多个不超过 10 秒的叙事片段，并生成可直接用于 Seedance 2.0 的英文多镜头视频提示词。用于已有精确 STYLE-BASE、approved ASSET-INDEX、对应实体资产和可定位单场剧本时，完成戏剧任务拆分、媒介一致的表演与运动调度、镜头设计、原文台词保真和精确 @参考调用；忠实继承真人、2D、3D、动漫画或混合媒介，不创建或修改上游风格与美术资产。
---

# AI Series Storyboard Master

## 目标

把一场戏转化为可执行的片段链：每个片段在同一空间内完成一个明确戏剧任务，时长不超过 10 秒，由 2–4 个有因果关系的镜头组成，并精确继承全局风格与已批准美术资产。

```text
单场剧本 + 已确认 STYLE-BASE + approved ASSET-INDEX + 当前实体资产
→ 上游校验 → 场戏拆分 → 场戏计划
→ 逐片段 Seedance 2.0 提示词 → 校验 → 直接 approved 交付
```

## 必读资源

- 任何正式产物：完整读取 [storyboard-artifact-contracts.md](references/storyboard-artifact-contracts.md)。
- 拆分片段、设计表演与镜头或执行语义审核：再完整读取 [cinematic-segmentation-protocol.md](references/cinematic-segmentation-protocol.md)。

## 输入门禁

开始前必须同时取得：

1. 一份剧本文件和一个可唯一定位的场次标题。
2. 来自兼容视觉 DNA Skill、且用户已确认的精确 `STYLE-BASE-[版本].md`；当前兼容 `ai-series-visual-dna` 与 `ai-xianxia-animation-visual-dna`。
3. 来自 `ai-series-art-director`、状态为 `approved` 的精确 `ASSET-INDEX-[版本].md`，其 `inherits-style` 与所选 STYLE-BASE 一致。
4. 索引指向的本场当前角色、群众、场景与重要道具 Markdown 文件。

缺少本场需要的主要角色、连续性群众系统、核心场景或重要道具资产，索引不是 `approved`，引用文件不存在，或版本与 STYLE-BASE 不一致时立即停止，返回缺失或过期清单。无连续性要求的一次性路人与普通杂物可以只用文本描述，不创建临时资产。

## 直接批准与版本迭代

- 场戏计划与全部片段首次通过校验后直接写为 `approved`，不创建内容相同的 `ready-for-review` 副本，不请求逐场审批确认。
- 用户明确提出镜头、文本分配、时长、资产引用或上游版本修改时，才创建一个新的 `approved` 版本；不得为状态迁移单独递增版本。
- `ready-for-review` 仅用于旧产物读取兼容，新流程不得创建。
- 已批准整场收到“继续”时，只返回精确视频提示词文件或说明外部生成执行边界；不得把未指定目标的“继续”推断为制作下一场。只有用户明确给出下一场 ID、标题或范围时才创建下一场。
- 不主动插入参考图、生图或其他可选门禁。

## 单场边界

- 默认每次只处理一个标准化场次 ID，例如 `EP001-SC001`。
- 输入包含多场时只处理用户指定场次；没有指定时先要求用户锁定一场。
- 不跨空间合并片段。同一场戏如果永久空间母体发生改变，停止并要求拆成两个源场次或补建场景资产。
- 不静默新增主要角色、核心场景、永久造型、固定道具或空间拓扑。

## 1｜上游核对

读取精确 STYLE-BASE、approved 索引以及本场涉及的当前实体文件：

- 核对索引当前文件、参考标签、实体 ID 与 STYLE-BASE。
- 从角色、群众、场景与道具文件分别原样提取 `Character Base`、`Crowd Base`、`Scene Base` 与 `Prop Base`。
- 登记创建时的索引快照，同时把每个实际使用的实体文件和参考标签写入产物。
- 新索引出现后，只比较本场引用实体是否改变；未引用资产的升级不得让本场分镜失效。

本场所需主要角色、连续性群众系统、核心场景或重要道具未建模时停止并交回 `ai-series-art-director`，不得用临时描述降级。

## 2｜场戏拆分

先识别整场的叙事功能、核心目标、起止状态、空间任务与前后连续性，再按以下任一真实变化切分片段：

- 角色目标或策略改变。
- 情绪层级跨越。
- 关键动作完成或信息权力转移。
- 观众需要新的观看位置才能理解下一步。
- 转场或下一戏剧任务开始。

先依据原文逐项估算台词的真实说话时间、动作完成时间、必要反应时间与转场时间，再求和得到场戏总时长；不得先设目标时长再向内容中填充节奏。情绪强度高不等于时长更长，动作与信息密度高时应主动压缩停顿。

每个片段必须大于 0 秒且不超过 10 秒，通常包含 2–4 个镜头。不得按固定秒数机械切块，不得把一个完整表演动作切断到两个片段。

把剧本中的台词、旁白和屏幕文字逐条登记为 `D001`、`D002`……；保留原文，不翻译、不润色。先写场戏计划，再写每个片段文件。

## 3｜片段设计

每个片段方案必须明确：

1. 片段编号与名称。
2. 核心场景和登场主要角色。
3. 叙事功能与戏剧目标。
4. 情绪推进与关键动作。
5. 原文台词、旁白或屏幕文字 ID。
6. 转场方式与前后片段衔接。
7. 精确角色、群众、场景、道具文件和 `@参考标签`。

每个镜头必须写景别、构图、机位角度、运镜和唯一的 `Dramatic execution`。不得再把 `Subject and action`、`Performance` 与台词拆成并列字段。`Dramatic execution` 必须按可见时间顺序，把主体目标、动作与关键姿势、STYLE-BASE 允许的表演/形变/线面/体积变化、说话时机、对手或环境即时反应和镜头最终落点写成一条因果链；禁止只写抽象情绪或在动作之后补挂孤立台词。

## 4｜Seedance 2.0 提示词

正式英文提示词固定三段：

- `[FOUNDATION]`：时长、16:9、精确参考标签，以及本片段实际使用的原样 Character Base、Crowd Base、Scene Base 与 Prop Base。
- `[ATMOSPHERE AND IMAGE QUALITY]`：只从 STYLE-BASE 转译 `Style Core`、`Visual Baseline`、`Color and Tonality`，不得建立第二套风格。
- `[VISUAL CONTENT]`：2–4 个连续时间区间的镜头，以及片段转场和进入下一片段的连续性。

所有控制指令使用英文。只有嵌入 `Dramatic execution` 句内的 `Dialogue [Dxxx]: "..."`、`Voice-over [Dxxx]: "..."`、`On-screen text [Dxxx]: "..."` 引号内允许保留剧本原语言。每个调用前后都必须有动作、可见表演、说话方式或即时反应，使原文成为动作过程的一部分；不得独立成行，不得新增未登记文本。

## 5｜校验与交付

写入后运行：

```powershell
python scripts/validate_storyboards.py <scene-plan-or-segment-files> --script <script.md> --style-base <STYLE-BASE.md> --asset-index <approved-ASSET-INDEX.md>
python scripts/validate_storyboards.py <segment-files> --script <script.md> --style-base <STYLE-BASE.md> --asset-index <approved-ASSET-INDEX.md> --plan <scene-plan.md>
```

校验失败时只修对应场戏或片段。首次合格交付状态直接为 `approved`；用户以后明确提出实质修改时才使用新版本，禁止生成仅状态不同的重复文件。

## 固定边界

- 不修改 STYLE-BASE、ASSET-INDEX、Character Base、Crowd Base、Scene Base 或 Prop Base。
- 不输出超过 10 秒的片段，不把多地点写进同一片段。
- 不为凑时长添加无信息空镜、重复反应、无动机慢推、装饰性停顿、慢动作或延迟转场；无法说明戏剧贡献的时间必须删除。
- 不翻译、改写或补写台词、旁白和屏幕文字。
- 不加入 STYLE-BASE 不支持的真人、2D、3D、动漫画、CG、游戏 key art、概念图本体、广告化处理、材质/线面规则或风格/IP；STYLE-BASE 已明确授权的媒介与渲染词不得被本 Skill 反向否决。
- 不生成角色图、场景图或视频；只生成场戏计划与视频提示词文件。

## 中文审阅派生输出

- 用户要求把正式片段翻译成中文供审核时，只在聊天中生成忠实派生稿，不修改英文正式文件。
- 人物、群众、场景和道具的中文展示名后不得追加资产 ID、版本号或 `@参考标签`；写“林渊：”，不得写“林渊（CHAR-001）：”。
- 技术 ID 只保留在独立的元数据、资产绑定或参考调用清单中，不与自然语言资产名称拼接。
- 原文台词、旁白和屏幕文字仍逐字保留，不因翻译审阅而改写。

## 交付

正式产物只写入项目根目录 `STORYBOARD/EPxxx/SCxxx/`，每场一个计划文件、每个片段一个文件，全部版本化并保留旧版。聊天只返回精确 `approved` 产物 ID、文件链接、片段数、总时长与校验状态，不请求逐场确认；除非用户明确要求，不粘贴完整提示词或内部推演。
