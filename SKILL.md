---
name: codex-image-gen
description: 调用本机已登录 ChatGPT 的 codex CLI 生成贴图/纹理——无缝平铺材质贴图、PBR 通道图（albedo/normal/roughness/metallic）、照片转贴图、贴图编辑与迭代精修（修接缝/调色/换材质风格）。用户提到"贴图、纹理、材质图、法线图、粗糙度图、金属度图、PBR、tiling、seamless、生成/改/修贴图、把这张照片做成贴图"时使用。仅限贴图纹理：UI 图标、插画、海报、概念图、特效精灵、SVG、3D 建模均不适用本技能。
---

# Codex 贴图生成

通过用户本机的 codex CLI（与其 ChatGPT 桌面客户端共享登录态）生成贴图，
生成走用户的 ChatGPT 订阅额度（每张约 30–60 秒、~1.3 万 token）。

**边界**：本技能只管贴图/纹理。UI 图标、插画、海报、概念图、特效精灵、
矢量 SVG、3D 模型一律不走本技能（建模由 agent 直接写 trimesh/Blender
脚本处理，不需要本技能的调用器）。

## 核心心法（决定贴图质量的三件事）

1. **无缝是验收出来的，不是许愿出来的**——提示词写 `seamless tileable`，
   交付前必须过 `--expect-tile` 程序化接缝检测。
2. **一套材质的通道图从同一张 albedo 派生**——normal/roughness/metallic
   用 `--edit albedo.png` 派生才能像素对齐，分别文生图会错位。
3. **迭代精修而非一次到位**——先出基准 albedo，之后每轮只改一个维度
   （接缝/配色/细节密度），`--edit` 上一版继续。

## 1. 环境自检（首次必做）

运行 `codex --version`（win 上可能是 `codex.cmd`）。找不到则按平台给安装指引：

- mac：`brew install codex`
- win / 任意平台：`npm install -g @openai/codex`
- 中国网络下 brew/npm 直连慢或 GitHub release 被重置时：npm 可换
  `--registry=https://registry.npmmirror.com`
- 已安装但脚本找不到：环境变量 `CODEX_BIN` 指向二进制路径

装完运行 `codex login status`。若未登录，**让用户本人运行一次 `codex login`**
（浏览器 OAuth，agent 无法代办），确认输出含 `Logged in using ChatGPT` 后继续。

## 2. 写提示词

完整英文提示词，一段式。模板见
`<skill目录>/references/prompt_library.md`（无缝 albedo、PBR 通道图派生、
照片转贴图、材质风格迁移、迭代修订指令）。要点：

- 尺寸写在提示词末尾（codex 会遵守），贴图常用 1024x1024
- 风格锚点（底色 + 点缀光色 + 质感关键词）全组复用同一段，写成
  `<...>` 槽位填项目自己的
- 编辑场景必须写**保持子句**（preserve layout/alignment...），
  否则模型会顺手重画纹理布局

## 3. 调用生成

跨平台脚本（`python3` 不存在则用 `python`）。三种模式：

```bash
# 文生图：无缝 albedo 贴图
python3 <skill目录>/scripts/gen_image.py \
  --prompt-file /tmp/prompt.txt \
  --out /abs/path/brick_albedo.png \
  --expect-size 1024x1024 \
  --expect-tile

# 参考图生成（同材质组风格锚定，--ref 可重复）
python3 <skill目录>/scripts/gen_image.py \
  --prompt-file /tmp/prompt.txt \
  --ref /abs/path/first_texture.png \
  --out /abs/path/next_texture.png \
  --expect-tile

# 编辑模式（派生通道图/修接缝/调色/迭代精修）
python3 <skill目录>/scripts/gen_image.py \
  --edit /abs/path/brick_albedo.png \
  --instruction "Convert this albedo texture into the matching tangent-space normal map ..." \
  --out /abs/path/brick_normal.png
```

脚本内部：codex 定位 → 登录预检 → `codex exec`（参考图经 `-i` 附图）→
尺寸/平铺程序化验收。生成失败自动重试一次并打印 codex 输出尾部辅助
诊断；`GEN_OK` 且各项 `OK` 才算过（SKIP 视为通过）。

要点：

- `--out` 用绝对路径；脚本会自动创建父目录
- 一次生成一张；一套材质逐张调用（见"批量一致性"）
- 连续失败看输出的 codex tail：多为额度/网络/提示词被安全策略拒

## 4. 一套标准 PBR 材质的工作流

1. 文生图出基准 albedo（`--expect-tile` 过接缝检测；FAIL 就加
   `seamless top-bottom and left-right wraparound` 补丁重生成）
2. 用 `--edit albedo` 依次派生 normal / roughness / metallic
   （提示词模板见提示词库"通道图派生"节）
3. 需要调色/换材质风格时，`--edit albedo` 改完 albedo 后，
   通道图必须从**新版 albedo 重新派生**，否则错位
4. 把生成产物路径告诉用户，并提示其归属（AI 生成、走谁的额度）

## 5. 批量一致性

同项目多张贴图（墙面/地面/金属一组）：

1. 先按第 4 节迭代出一张"风格定稿"
2. 其余各张全部 `--ref 定稿.png` + 各自材质提示词（提示词里仍要重复
   风格锚点措辞，双重锚定）
3. 交付前逐张过 `--expect-tile`

## 排障

| 现象 | 处理 |
|---|---|
| `codex not found` | 见步骤 1 安装指引；或设 `CODEX_BIN` |
| `not logged in` | 用户本人跑一次 `codex login` |
| `output not created` | 看脚本打印的 codex output tail：多为额度/网络；脚本已自动重试一次 |
| 尺寸不符 | 提示词末尾尺寸写明确（如 `1024x1024`），重新生成 |
| 接缝明显 | 加 `seamless ... wraparound` 补丁重生成；仍 FAIL 就 `--edit` 该图追加 "remove visible seams at tile edges" |
| 通道图错位 | 通道图必须从当前版 albedo 用 `--edit` 派生，不能单独文生图 |
| 编辑后纹理布局变了 | 指令里补保持子句（preserve texture layout and alignment） |
| 超时 900s | `--timeout` 调大或重试；连续超时让用户检查网络 |

## 分发说明（给安装本技能的人）

把整个 `codex-image-gen/` 目录放入 `~/.agents/skills/`（全局）或项目内
`.agents/skills/`（单项目），重启 ZCode 会话即可被发现。首次使用需本机已
安装 codex CLI 并完成 `codex login`（与 ChatGPT 桌面客户端共享登录态，
装过桌面版通常无需再登录）。可选依赖：`pip3 install pillow`（开启平铺
程序化验收）。
