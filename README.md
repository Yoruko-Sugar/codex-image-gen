# codex-image-gen

一个 [ZCode](https://z.ai)/agent 技能：驱动本机已登录 ChatGPT 的 **codex CLI** 生成贴图/纹理。

不需要 OpenAI API key——生成走你已有的 ChatGPT 订阅额度（codex 与 ChatGPT 桌面客户端共享登录态）。

**范围只限贴图**：无缝平铺材质贴图、PBR 通道图（albedo/normal/roughness/metallic）、照片转贴图、贴图编辑与迭代精修。UI 图标、插画、海报、概念图、特效精灵、SVG、3D 建模不在本技能范围内。

## 能力

| 模式 | 命令 | 适用 |
|---|---|---|
| 文生图 | `gen_image.py` | 无缝 albedo 材质贴图（程序化接缝验收） |
| 参考图生成 | `gen_image.py --ref` | 同一材质组的多张贴图风格锚定（经 `codex exec -i` 附图） |
| 编辑模式 | `gen_image.py --edit` | 从 albedo 派生 normal/roughness/metallic、修接缝、调色、换材质风格 |

三条核心心法：

1. **无缝是验收出来的，不是许愿出来的**——提示词写 `seamless tileable`，交付前必须过 `--expect-tile` 程序化接缝检测
2. **一套材质的通道图从同一张 albedo 派生**——用 `--edit albedo.png` 派生才能像素对齐，分别文生图会错位
3. **迭代精修而非一次到位**——每轮只改一个维度（接缝/配色/细节密度），`--edit` 上一版继续

## 安装

```bash
# 全局（所有项目可用）
git clone https://github.com/Yoruko-Sugar/codex-image-gen.git ~/.agents/skills/codex-image-gen

# 或单项目
git clone https://github.com/Yoruko-Sugar/codex-image-gen.git .agents/skills/codex-image-gen
```

重启 ZCode 会话即可被发现。

前置条件：

- **codex CLI** 已安装并登录（`brew install codex` 或 `npm i -g @openai/codex`，然后本人跑一次 `codex login`）
- 可选：`pip3 install pillow`（开启平铺接缝程序化验收）

## 用法

```bash
# 无缝 albedo 贴图（文生图）
python3 scripts/gen_image.py --prompt-file prompt.txt \
  --out brick_albedo.png --expect-size 1024x1024 --expect-tile

# 从 albedo 派生 normal map（编辑模式，像素对齐）
python3 scripts/gen_image.py --edit brick_albedo.png \
  --instruction "Convert this albedo texture into the matching tangent-space normal map: raised areas at panel seams, recessed scratches, neutral blue-purple encoding, pixel-aligned with the source, 1024x1024" \
  --out brick_normal.png

# 同组下一张贴图，挂组内定稿做风格锚定
python3 scripts/gen_image.py --prompt-file ground.txt \
  --ref brick_albedo.png --out ground.png --expect-tile
```

提示词模板库（无缝 albedo、PBR 通道图、照片转贴图、材质风格迁移、迭代修订指令）见
[references/prompt_library.md](references/prompt_library.md)。

脚本内置程序化验收：尺寸、平铺接缝，`GEN_OK` 且各项 `OK` 才算过；
生成失败自动重试并打印 codex 输出尾部辅助诊断。
