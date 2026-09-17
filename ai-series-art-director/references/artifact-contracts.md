# AI 长剧美术资产契约

## 目录

1. [共同规则](#共同规则)
2. [资产索引](#资产索引)
3. [角色资产](#角色资产)
4. [群众演员资产](#群众演员资产)
5. [场景资产](#场景资产)
6. [重要道具资产](#重要道具资产)
7. [版本与交接](#版本与交接)

## 共同规则

- 正式目录固定为项目根目录 `ART/`。
- 版本只允许 `vN.N` 或 `draft-v0.N`。
- 每份产物必须记录精确 `inherits-style`；角色、群众、场景与道具实体还必须记录精确 `inherits-index`。
- 禁止使用 `latest`、`current` 或无版本引用。
- 正式英文代码块只使用英文；角色名、群众系统名、场景名、道具名、源材料定位和中文建模方案可使用中文。
- 每个 Model-Sheet Prompt 必须显式写明精确 STYLE-BASE 的 `live-action` 真人电影本体，转译相关材质、成像与 `cinematic VFX` 规则；不得只写 `follow STYLE-BASE`。不接收动画或混合动画风格，不把视效制作技术写成 `3D VFX` 等媒介标签。
- 保留既有建模字段与产物结构。源材料事实、用户偏好与 `design-choice`（设计选择）在中文建模方案中区分；普通造型缺失时主动设计，发布后作为连续性锚点。不适用字段填原因与对应形态，不改字段名、不强制非人角色长出人类头发或四肢。
- 固有超自然特征、世界内稳定结构和已建立的允许状态须进入对应精炼 Base；不夹带具体施法动作、剧情结果或全局风格。题材表现不能只存在于长图版提示词中。
- 不覆盖旧版。内容或引用变化时写新版本文件。

```text
ART/
├── ASSET-INDEX-[版本].md
├── characters/CHAR-001-[版本].md
├── crowds/CROWD-001-[版本].md
├── scenes/SCN-001-[版本].md
├── props/PROP-001-[版本].md
└── references/
    ├── CHAR-001-REF-[版本].png
    ├── CROWD-001-REF-[版本].png
    ├── SCN-001-REF-[版本].png
    └── PROP-001-REF-[版本].png
```

## 资产索引

文件名与首行标题必须完全一致：

```markdown
## ASSET-INDEX-draft-v0.1
- inherits-style: STYLE-BASE-v1.0
- source: scripts/series.md
- coverage: complete
- status: approved

### 主要角色
| Asset ID | 名称 | 收录依据 | 出现范围 | 当前文件 | 参考标签 |
|---|---|---|---|---|---|
| CHAR-001 | 林默 | 核心行动者 | EP001–EP010 | characters/CHAR-001-v1.0.md | @CHAR-001-REF-v1.0 |

### 群众演员
| Asset ID | 名称 | 收录依据 | 出现范围 | 当前文件 | 参考标签 |
|---|---|---|---|---|---|
| CROWD-001 | 城防军 | 共享制服与层级系统需跨场连续 | EP001-SC002, EP002-SC004 | crowds/CROWD-001-v1.0.md | @CROWD-001-REF-v1.0 |

### 核心场景
| Asset ID | 名称 | 空间母体依据 | 出现范围 | 当前文件 | 参考标签 |
|---|---|---|---|---|---|
| SCN-001 | 林宅正厅 | 稳定空间母体 | EP001-SC001 | scenes/SCN-001-v1.0.md | @SCN-001-REF-v1.0 |

### 重要道具
| Asset ID | 名称 | 收录依据 | 出现范围 | 当前文件 | 参考标签 |
|---|---|---|---|---|---|
| PROP-001 | 铜制密函筒 | 跨角色流转并承载关键证据 | EP001-SC003–EP003-SC006 | props/PROP-001-v1.0.md | @PROP-001-REF-v1.0 |
```

新索引固定依次包含四张表：`主要角色`、`群众演员`、`核心场景`、`重要道具`。某类无资产时保留表头与分隔行、不写实体行。兼容旧索引时允许缺少 `群众演员` 与 `重要道具` 两张表，并按 0 项处理；重新发布新版本时必须补齐四张表。

为兼容现有分镜读取器，索引在最后一张表末行后以单个换行结束，不追加空白行或说明段落；否则末表可能漏读。美术校验器须拦截末尾空白行，发布前还须核对读取到的四类资产数量与本轮审计范围一致。

新产物状态固定为：

- `approved`：当前资产集合已完成审核与校验，可直接交给分镜阶段；所有行必须写精确文件与参考标签。

`awaiting-confirmation`、`confirmed-for-modeling` 与 `awaiting-asset-approval` 仅用于旧产物读取兼容，新流程不得创建。首次发布前先锁定精确索引 ID，让全部实体继承该 ID，再把同一索引写为 `approved`；不得为状态迁移复制内容相同的新版本。

正式实体行使用：

```text
characters/CHAR-001-v1.0.md | @CHAR-001-REF-v1.0
crowds/CROWD-001-v1.0.md | @CROWD-001-REF-v1.0
scenes/SCN-001-v1.0.md | @SCN-001-REF-v1.0
props/PROP-001-v1.0.md | @PROP-001-REF-v1.0
```

## 角色资产

```markdown
## CHAR-001-v1.0｜林默
- inherits-style: STYLE-BASE-v1.0
- inherits-index: ASSET-INDEX-v1.0
- source: EP001-SC001, EP001-SC004
- coverage: complete
- reference-label: @CHAR-001-REF-v1.0
- reference-image: pending

### 建模方案
1. 角色定位：
2. 叙事作用：
3. 核心识别点：
4. 年龄与外貌：
5. 发型：
6. 服装：
7. 配色：
8. 配饰、武器与道具：
9. 气质关键词：
10. 连续性锚点：

### Character Model-Sheet Prompt
~~~text
[直接可用的英文图片提示词]
~~~

### Character Base
~~~text
[35–100 个英文词的实体精炼设定]
~~~
```

Model-Sheet Prompt 必须显式包含真人电影表达与以下控制短语：`16:9`、`pure white background`、`upper-left`、`lower-left`、`right side`、`front view`、`profile view`、`back view`、`continuity anchors`。非人角色的面部特写可转为核心识别部位，三视图仍核对同一形态。纯白背景只简化展示，不改变固有透明、发光、悬浮或衣料特性；局部边缘与明暗须使白底上的结构可辨，不能借识别之名删除实体特征。

`Character Base` 保存年龄或生命阶段、可见形态、发型/对应结构、服装、配色、配饰、固有超自然特征及连续性锚点。允许稳定的半透明身体或附属光纹，不写本场正在施法。禁止背景、空间、剧情动作、情绪结果、摄影机、镜头、画幅和全局画质词。

## 群众演员资产

```markdown
## CROWD-001-v1.0｜城防军
- inherits-style: STYLE-BASE-v1.0
- inherits-index: ASSET-INDEX-v1.0
- source: EP001-SC002, EP002-SC004
- coverage: complete
- reference-label: @CROWD-001-REF-v1.0
- reference-image: pending

### 建模方案
1. 群体定位：
2. 叙事与空间作用：
3. 组织与层级构成：
4. 人口构成与差异范围：
5. 体态与面貌分布：
6. 发型与妆容系统：
7. 服装与制服层级：
8. 配色、配饰与携带物：
9. 职业姿态与动作语汇：
10. 连续性锚点与允许变化：

### Crowd Model-Sheet Prompt
~~~text
[直接可用的英文图片提示词]
~~~

### Crowd Base
~~~text
[45–120 个英文词的群体精炼设定]
~~~
```

Model-Sheet Prompt 必须显式包含真人电影表达，并包含：`16:9`、`pure white background`、`group lineup`、`rank variations`、`front view`、`profile view`、`back view`、`continuity anchors`、`no duplicated faces`。图版表现一个群体造型系统，可展示 6–12 名代表性个体与层级变体，不固化每场人数、站位和脸孔。非人群体按世界设定展示可辨个体差异，固有超自然特征不因白底被删掉；无层级者说明同级差异，不虚构组织等级。

`Crowd Base` 保存组织身份、构成与差异范围、体态面貌、发型妆容、制服层级、配色、携带物、职业姿态、群体固有超自然特征、连续性锚点与允许变化。禁止具体场景、剧情动作、固定人数、固定队形、摄影机、镜头、画幅和全局画质词。

## 场景资产

```markdown
## SCN-001-v1.0｜林宅正厅
- inherits-style: STYLE-BASE-v1.0
- inherits-index: ASSET-INDEX-v1.0
- source: EP001-SC001, EP002-SC003
- coverage: complete
- reference-label: @SCN-001-REF-v1.0
- reference-image: pending

### 建模方案
1. 场景名称：
2. 场景作用：
3. 空间类型：
4. 时代与世界观属性：
5. 全景布局结构：
6. 主视觉焦点：
7. 关键道具：
8. 色彩氛围：
9. 光线逻辑：
10. 可调度区域：
11. 角色可站位区域：
12. 连续性锚点：

### Scene Model-Sheet Prompt
~~~text
[直接可用的英文图片提示词]
~~~

### Scene Base
~~~text
[40–120 个英文词的空间精炼设定]
~~~
```

Model-Sheet Prompt 必须显式包含真人电影表达，并包含 `16:9`、`2x2 four-panel grid`、`same scene`、`full-scene overview`、`feature-focused panel`、`defining scene features`；还必须明确 `foreground`、`midground`、`background`、`entrance`、`exit`、`key props`、`light source`、`blocking zones` 与 `standing positions`。四格保持同一稳定空间母体、固定结构、材质、道具位置与光源逻辑，但信息层级不同：至少一格完整广角全景，至少一格非广角特征视图，其余格补足调度关系或核心特征。特征格须与全景格核对空间归属、尺度和固定位置，不得变成孤立产品图或拼入不同地点/条件变体。实景、实体布景或数字环境均可采用；悬浮山门、洞天和超常建筑保留世界内稳定相对布局、出入方式、可行动区域及视效融合，不要求现实工程可建。

`Scene Base` 保存稳定空间、材料、前中远景关系、出入口、固定道具、世界内光源位置、调度与站位区域；悬浮平台的固定关系、洞天入口或常驻超自然环境现象属于空间事实，不是全局风格词。禁止具体角色、剧情动作、对白、摄影机、镜头、画幅和全局画质词。

## 重要道具资产

```markdown
## PROP-001-v1.0｜铜制密函筒
- inherits-style: STYLE-BASE-v1.0
- inherits-index: ASSET-INDEX-v1.0
- source: EP001-SC003, EP002-SC005, EP003-SC006
- coverage: complete
- reference-label: @PROP-001-REF-v1.0
- reference-image: pending

### 建模方案
1. 道具名称：
2. 道具类别：
3. 叙事功能：
4. 归属与流转：
5. 尺寸与人体尺度：
6. 轮廓与核心识别点：
7. 结构与构造：
8. 材料与制造工艺：
9. 配色与表面状态：
10. 使用、握持与佩戴逻辑：
11. 状态谱系与变化触发：
12. 连续性锚点：

### Prop Model-Sheet Prompt
~~~text
[直接可用的英文图片提示词]
~~~

### Prop Base
~~~text
[40–120 个英文词的道具精炼设定]
~~~
```

Model-Sheet Prompt 必须显式包含真人电影表达，并包含：`16:9`、`neutral background`、`three-quarter view`、`front view`、`profile view`、`back view`、`top view`、`scale reference`、`material details`、`continuity anchors`。道具须有世界内自洽的结构、尺度、材质和使用逻辑，但不必现实可制造；法器可悬浮、自发光或非接触操控，不强加机械解释。中性背景不取消固有超自然特征，也不以强光遮蔽结构。如原文存在开启、破损、染血、封印解除等状态，只展示已成立的状态变体，保持同一实体身份。

`Prop Base` 保存类别、尺寸、轮廓、结构、材料、构成痕迹、固定标记、接触或非接触操控关系、固有超自然特征、初始状态、已建立的允许状态及连续性锚点。描述悬浮/激活条件不等于执行当前施法；禁止当前持有者动作、剧情结果、场景、摄影机、镜头、画幅和全局画质词。

## 版本与交接

- 索引、角色、群众、场景、道具各自独立版本化。
- STYLE-BASE 主版本改变时，全部美术资产失效并重建。
- STYLE-BASE 次版本改变时，全部美术资产必须重新校验；可见结果不变时允许只升级继承声明与资产次版本。
- 单个实体修订时只升级该实体，并写新索引指向新版本；其他实体保持不变。
- 群众系统的制服层级、人口边界或组织身份变化，以及重要道具的核心结构、尺寸、固定标记或状态谱系变化，均属于主版本变化。
- `ai-series-storyboard-master` 只允许读取状态为 `approved` 的精确索引版本。
- 参考图缺失不阻断文本提示词交接；参考标签仍必须存在并标记 `reference-image: pending`。
- 后补参考图时升级实体次版本，并让新实体文件、`reference-label`、`reference-image` 与图片文件使用同一版本；随后直接写一个新的 `approved` 索引指向该版本，不创建图片审批状态。
- 只有用户明确提出修改时才升级版本；禁止仅因确认或批准状态变化创建新版本。
