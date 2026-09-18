# 极简白膜与 Blender MCP 执行协议

## 目标与边界

白膜只验证“谁在哪里、做了什么、摄影机能否看清、片段如何衔接”，不是美术复刻或精细表演工程。严格保留已批准 VISUAL CONTENT 的片段时长、镜头边界、主体人数、关键动作顺序、方向和道具状态；通过粗几何与少量关键姿态表达，不另写剧情。

- 每个片段独立建模、渲染和交付；默认不拼接，也不附赠合辑。
- 角色保留参考图可辨的头发/服装大轮廓及必要体型差异。可用简单人形、圆柱、球、锥体，不强制全套骨骼。
- 默认不做眼球、眉毛、嘴型、手指关节、衣料褶皱、精细发丝、伤疤拓扑或物理布料模拟。确实影响关键信息时，用单个简单标记或部件表达即可。
- 场景只做可行动面、出入口、边界、遮挡和关键道具。远山、云雾等用低复杂度体块，不能占用超过主调度的工作量。
- 拿取/披覆/遮挡/触头用手部代理、父子关系或约束；优先消除明显穿透、悬空、错手、丢失物件，不追求亚毫米拟合。
- 保留对白占时及可见身体反应，不要求口型；无音轨、无字幕、无叠字。声音与原文语义列入 unverifiable。

## 输入与路径

读取本片段的精确分镜、STYLE-BASE、approved 索引、实体和每张登记图。记录简短 observations 与 retained_features，三视图不复制成人数，四宫格不拆成四个地点。图片 pending、损坏或版本不一致时阻塞对应白膜，不生成临时替代图。

绝对 reference-image 直接使用。显式登记的 reference-path-root 优先（包含项目根目录的现有约定也可读取）；否则相对实体文件所在目录。路径必须唯一解析并与登记相符，不猜同名图。

## 必须经 Blender MCP 执行

1. 发现当前可调用的 Blender MCP 工具，先读取场景/文件状态。连接失败时诊断桥接进程与本地端口，不连续重复相同失败。
2. 可启动已安装的本地 MCP 桥接服务；这是连接准备，不算建模已完成。Windows 后台助手用隐藏窗口；不自动安装插件、不持久改变安全设置。
3. 在新建、隔离且可追踪的场景中工作。保留用户已有对象、活动文件与未保存状态，禁止全局清场或覆盖已有工程。
4. 通过 MCP 实际执行建模、关键帧、镜头设置、工程保存及渲染。先用专用工具；没有对应功能时才用 execute_blender_code。MCP 提供的后台文件执行工具也属于 MCP，但必须披露所用方式。
5. 外部终端可做文件操作、FFmpeg 编码/解码及测试，不能偷偷承担 Blender 制作再声称 MCP 完成。MCP 无法运行时报告阻塞；只有用户明确同意才能使用旧 CLI 路线。
6. 长渲染拆成可追踪的镜头批次，或使用工具明确支持的任务机制。不因超时盲目重发，先检查当前状态和已有输出。每次实际工具调用保留简洁返回记录。

工具名称以当前发现的接口为准，不假定通用 API。已验证的本地桥接实现支持 execute_blender_code，返回值使用 result 字典。scripts/blender_mcp_job.py 可经该工具调用：prepare 创建隔离场景，render_shots 渲染选定镜头，finish 保存独立工程并清理本任务场景。它不启动 Blender、不自行冒充 MCP 客户端。

若本机已安装 Blender 官方 MCP 扩展且交互端口未启动，可以使用其正式桥接命令启动独立后台服务：`blender --background --factory-startup --online-mode --addons <已发现的扩展模块名> --command blender_mcp --host 127.0.0.1 --port <已配置端口>`。先核实扩展位置和监听端口；不硬编码另一台机器的路径，不持久更改用户偏好。此命令只启动桥接，后续制作仍须调用 MCP 工具。本地已验证的模块名为 `bl_ext.user_default.mcp`，端口9876；它们是本机实测信息，不是通用默认。一次性后台文件接口超时时，检查环境和桥接，不盲目重复等待。

## 执行描述与可复现文件

沿用原来源指纹、资产绑定、shots、unverifiable、builder 结构，新文件使用 schema_version: 2，并增加：

~~~json
{
  "execution": {"backend": "blender-mcp", "tool": "实际工具名"},
  "modeling": {"level": "minimal-blocking"},
  "review": {"mode": "normal-speed"},
  "shots": [{"id": 1, "review_frames": []}],
  "contacts": []
}
~~~

以上仅展示新增/调整字段，不是完整 spec。每镜仍记录 start/end、camera、camera_plan、action_plan、visible_objects、state_in/state_out；review_frames 可以为空，不再强制首中尾。contacts 只为确有必要的接触建立少量检查点，也允许为空。每个已使用资产都要绑定对象，不能靠精简删掉剧情中的实体。

WB 文件仍位于本场 PREVIS/，每片段独立使用 EPxxx-SCxxx-SEGxxx-WB-vN.N：
.json（执行描述）、.py（建模源）、.blend、.mp4、-MCP.json（实际调用记录）、-QA.json。固定版本，不覆盖旧产物。共享源码若使用，须由入口指纹绑定。

帧区间为零起点左闭右开，Blender 帧加一。保留源时长；默认960×540、24fps，按项目需要调整，快速技术测试可降低分辨率。渲染输出图片序列不等于逐帧检查，不生成密集 QA 联系表。

建模源提供 build(spec, base_dir)，在驱动器已经隔离的场景中建立对象与关键帧；不得清理其他场景、启动外部进程或依赖工程关闭后失效的临时回调。单位米，Z向上；左右手按角色自身定义。

## 校验与执行入口

~~~powershell
python scripts/whitebox_previs.py validate <WB.json>
~~~

通过 MCP 执行（具体工具名需先发现）：

~~~python
import runpy
job = runpy.run_path("<skill>/scripts/blender_mcp_job.py")
result = job["prepare"]("<WB.json>")
# 后续工具调用：
result = job["render_shots"]("<WB.json>", [1, 2])
result = job["finish"]("<WB.json>")
~~~

将真实 MCP 调用及返回存入 -MCP.json 后，编码独立片段：

~~~powershell
python scripts/whitebox_previs.py finalize-mcp <WB.json> --receipt <WB-MCP.json>
python scripts/whitebox_previs.py check <WB.json> --review <visual-review.json>
~~~

旧 schema 1 兼容读取；旧直接命令行 render 仅在用户明确同意后使用 --legacy-cli，不是自动后备路径。MCP receipt 是可追溯记录，不是单靠字符串就能证明的执行事实，必须对应实际工具调用。

## 检查尺度与完成判定

1. 对每个独立视频做一次轻量媒体检查：分辨率、时长、帧率、帧数、可完整解码、无音轨/字幕流。
2. 正常速度通看一次，只关注人物可辨、空间/轴线、主要动作、明显穿透/错手、镜头是否看清、无叠字。
3. 只有发现具体问题才暂停查看相应时刻，修复对应镜头；不逐帧检查、不按固定fps抽取大量截图、不追求无关造型细节。
4. 若当前工具无法真正播放/理解完整视频，记录技术流程已跑通但视觉待通看；最多查看少量整体预览，不以密集截图替代通看，也不填虚假观看证据。
5. 修复后只复核受影响片段；无新失败或风险，不扩大检查。

新视觉记录使用片段级结构：

~~~json
{
  "spec_sha256": "...", "video_sha256": "...", "blend_sha256": "...",
  "reviewer": "实际观看者",
  "method": "normal-speed-playback",
  "playback_speed": 1,
  "watched_range": [0, 360],
  "checks": {"identity": true, "action": true, "camera": true, "continuity": true, "no_text": true},
  "issues": [],
  "evidence": "实际通看的方式与结论；仅在有问题时记对应时间"
}
~~~

complete 需要结构、媒体和真实通看均通过。只有渲染/编码成功时为 rendered，视觉待通看；依赖、绑定或执行失败为 blocked。不要把正常速度通看升级成逐帧验收，不用质感瑕疵阻塞已能验证调度的极简白膜。
