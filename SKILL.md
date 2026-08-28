---
name: codex-image-gen
description: 调用本机已登录 ChatGPT 的 codex CLI 生成项目美术资产——图片（贴图、UI 图标、插画、特效精灵、概念图、关键视觉、海报）、图像编辑与风格迁移（改图/换风格/迭代精修）、程序化矢量 SVG（图标/logo/九宫格边框）与 3D 模型（trimesh/Blender headless 导出 GLB）。用户需要任何 AI 生成的图片/贴图/图标/logo/3D 模型/素材，或要"改一下这张图"、"换个风格"、"P个图"、"来一张图"、"建个模型"、"生成个图标"时使用。
---

# Codex 生图

通过用户本机的 codex CLI（与其 ChatGPT 桌面客户端共享登录态）生成图片，
生成走用户的 ChatGPT 订阅额度（每张约 30–60 秒、~1.3 万 token）。

## 核心心法（决定出图质量的三件事）

1. **选对生成路径**：位图（氛围/材质/插画）→ gen_image.py；矢量
   （图标/logo/边框，要精确色值或无限缩放）→ gen_svg.py；立体 → gen_model.py。
2. **用参考图锚定**：codex 支持 `-i` 附图。风格一致性靠 `--ref` 挂已成品，
   不靠复述提示词——这是官方 showcase 项目（photobooth / rift-vox 等）的标准做法。
3. **迭代精修而非一次到位**：先出一张基准图，之后每轮只改一个维度
   （`--edit` 上一版 + 单项修订指令）。showcase 里所有惊艳的作品都是
   6 轮左右迭代的产物，没有一张是一次成的。

## 生成路径选择

| 需求 | 路径 | 理由 |
|---|---|---|
| 贴图/精灵/概念图/关键视觉/海报 | `gen_image.py` 文生图 | 氛围与材质细节 |
| 已有图改风格/改局部/派生通道图 | `gen_image.py --edit` | 官方风格迁移公式 |
| 同批多张、风格要统一 | `gen_image.py --ref` | 挂第一张成品当锚 |
| UI 图标/logo/九宫格边框/示意图 | `gen_svg.py` | 无限缩放、色值精确、可代码微调 |
| 低模硬表面 3D 资产 | `gen_model.py` | GLB 直出 |

拿不准位图还是矢量时：要"感觉"选位图，要"精确"选矢量；图标集两路都
可以，矢量更适合批量同风格。

## 1. 环境自检（首次必做）

运行 `codex --version`（win 上可能是 `codex.cmd`）。找不到则按平台给安装指引：

- mac：`brew install codex`
- win / 任意平台：`npm install -g @openai/codex`
- 中国网络下 brew/npm 直连慢或 GitHub release 被重置时：npm 可换 `--registry=https://registry.npmmirror.com`
- 已安装但脚本找不到：环境变量 `CODEX_BIN` 指向二进制路径

装完运行 `codex login status`。若未登录，**让用户本人运行一次 `codex login`**
（浏览器 OAuth，agent 无法代办），确认输出含 `Logged in using ChatGPT` 后继续。

## 2. 写提示词

完整英文提示词，一段式。模板与手法见
`<skill目录>/references/prompt_library.md`——按场景取用（无缝贴图/特效精灵/
透明底精灵/UI 图标/关键视觉/角色设定/序列帧/场景背景/九宫格/PBR 通道图/海报，
以及官方风格迁移四段公式）。要点：

- 尺寸写在提示词末尾，codex 会遵守
- 编辑场景必须写**保持子句**（preserve identity, pose, composition…），
  否则模型会顺手重画构图
- 修订指令每轮只改一个维度，先说保持、再说修改

## 3. 调用生成

跨平台脚本（`python3` 不存在则用 `python`）。三种模式：

```bash
# 文生图（模板 + 验收开关）
python3 <skill目录>/scripts/gen_image.py \
  --prompt-file /tmp/prompt.txt \
  --out /abs/path/to/output.png \
  --expect-size 512x512 \
  --expect-black-bg      # 特效精灵用
  --expect-tile          # 无缝贴图用
  --expect-alpha         # 透明底精灵用

# 参考图生成（风格/主体锚定，--ref 可重复）
python3 <skill目录>/scripts/gen_image.py \
  --prompt-file /tmp/prompt.txt \
  --ref /abs/path/anchor.png \
  --out /abs/path/to/output.png

# 编辑模式（风格迁移/局部修改/迭代精修；指令长就用 --instruction-file）
python3 <skill目录>/scripts/gen_image.py \
  --edit /abs/path/to/source.png \
  --instruction "Keep the exact composition and framing. Change only the palette to warm amber accents." \
  --out /abs/path/to/output.png
```

脚本内部：codex 定位 → 登录预检 → `codex exec`（参考图经 `-i` 附图）→
尺寸/黑底/透明/平铺程序化验收。生成失败自动重试一次并打印 codex 输出尾部
辅助诊断；`GEN_OK` 且各项 `OK` 才算过（SKIP 视为通过）。退出码见各脚本头注释。

要点：

- `--out` 用绝对路径；脚本会自动创建父目录
- 一次生成一张；多张就多次调用（见"批量一致性"）
- 连续失败看输出的 codex tail：多为额度/网络/提示词被安全策略拒

## 4. 迭代精修工作流（高质量输出的来源）

1. 第一轮用模板文生图出基准图，只求构图/风格方向正确
2. 看图（Read 工具直接看 PNG），确定下一轮唯一要改的维度
3. `--edit 基准图 --instruction "<保持子句> + <单项修改>"` 出第二版
4. 重复 2–3，通常 2–4 轮收敛；满意的版本留作后续同批素材的 `--ref` 锚

把生成产物路径告诉用户，并提示其归属（AI 生成、走谁的额度）。

## 5. 批量一致性

同批 N 张（图标集/贴图组/序列帧）：

1. 先按第 4 节迭代出一张"风格定稿"
2. 其余 N-1 张全部 `--ref 定稿.png` + 各自内容提示词（提示词里仍要重复
   风格锚点措辞，双重锚定）
3. 交付前并排检查（可用 PIL 拼贴成一张 contact sheet 给自己看）

## 6. 程序化矢量（gen_svg.py）

codex 直接手写 SVG——适合 UI 图标/logo/九宫格边框/示意图：无限缩放不糊、
品牌色硬编码精确、体积小、后续可用代码继续调。

```bash
python3 <skill目录>/scripts/gen_svg.py \
  --prompt-file /tmp/brief.txt \
  --out /abs/path/to/icon.svg \
  --viewbox 512
```

脚本校验：XML 可解析、viewBox 匹配、含矢量元素、无位图嵌入。
图标集批量：同一段风格描述 + 各图标主体，逐个调用；SVG 文本可直接
diff 和微调，比位图批量更稳。

## 7. 3D 建模（gen_model.py，codex + trimesh/Blender headless）

程序化建模（写 Python 脚本 → headless 执行 → 导出 GLB），适合低模硬表面：
机甲部件、武器、无人机、道具、建筑模块。

引擎两档（`--engine`，默认 auto）：

- **python（首选）**：纯 trimesh 建模，无 Blender 依赖——快（~100s）、
  零崩溃弹窗。前置：`pip3 install trimesh numpy`（国内加镜像
  `-i https://pypi.tuna.tsinghua.edu.cn/simple`）
- **blender（备选）**：Blender headless，支持骨骼/修改器等复杂特性。
  前置：mac `brew install --cask blender`，win 官网安装且 `blender` 在 PATH。
  Blender 崩溃弹窗可全局关闭：
  `defaults write com.apple.CrashReporter DialogType none`

能力边界：低模/中模硬表面可行；高精度生物雕刻、复杂角色拓扑、
影视级骨骼动画不可行，仍需人工美术。

```bash
python3 <skill目录>/scripts/gen_model.py \
  --spec /path/to/spec.md --out /path/to/model.glb --max-tris 1500
```

流程：写规格 markdown（格式/轴/单位、原点、目标尺寸、面数预算低模常
≤1500 面、材质槽数量、与贴图组一致的风格锚点；模板见
`<skill目录>/assets/model_spec_template.md`）→ 调用（自动前置检查 → 生成 →
GLB magic/JSON 校验，实测 python 引擎 ~100s/个、Blender ~300s/个）→
`GEN_OK` 后在目标引擎加载检查包围盒/原点/材质槽 → 保留 build 脚本可复现。

## 排障

| 现象 | 处理 |
|---|---|
| `codex not found` | 见步骤 1 安装指引；或设 `CODEX_BIN` |
| `not logged in` | 用户本人跑一次 `codex login` |
| `output not created` | 看脚本打印的 codex output tail：多为额度/网络；脚本已自动重试一次 |
| 尺寸不符 | 提示词末尾尺寸写明确（如 `512x512`），重新生成 |
| 接缝明显 | 加 `seamless ... wraparound` 补丁重生成 |
| 编辑后构图变了 | 指令里补保持子句（preserve composition/pose/framing） |
| 透明底不透明 | 提示词加 `isolated on fully transparent background`，配 `--expect-alpha` |
| SVG 嵌了位图 | 提示词强调 `NO <image>, pure vector only` 重生成 |
| 超时 900s | `--timeout` 调大或重试；连续超时让用户检查网络 |

## 分发说明（给安装本技能的人）

把整个 `codex-image-gen/` 目录放入 `~/.agents/skills/`（全局）或项目内
`.agents/skills/`（单项目），重启 ZCode 会话即可被发现。首次使用需本机已
安装 codex CLI 并完成 `codex login`（与 ChatGPT 桌面客户端共享登录态，
装过桌面版通常无需再登录）。可选依赖：`pip3 install pillow`（开启黑底/
透明/平铺验收）、`pip3 install trimesh numpy`（3D 首选引擎）。
