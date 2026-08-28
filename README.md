# codex-image-gen

一个 [ZCode](https://z.ai)/agent 技能：驱动本机已登录 ChatGPT 的 **codex CLI** 生成项目美术资产。

不需要 OpenAI API key——生成走你已有的 ChatGPT 订阅额度（codex 与 ChatGPT 桌面客户端共享登录态）。

## 能力

| 路径 | 脚本 | 适用 |
|---|---|---|
| 文生图 | `scripts/gen_image.py` | 贴图、特效精灵、UI 图标、概念图、关键视觉、海报 |
| 参考图生成 | `scripts/gen_image.py --ref` | 同批多张素材的风格锚定（经 `codex exec -i` 附图） |
| 图像编辑/风格迁移 | `scripts/gen_image.py --edit` | 改风格、局部修改、迭代精修（官方四段式提示词公式） |
| 程序化矢量 | `scripts/gen_svg.py` | 图标/logo/九宫格边框：无限缩放、色值精确、可代码微调 |
| 3D 建模 | `scripts/gen_model.py` | 低模硬表面 GLB（trimesh 纯 Python 首选，Blender headless 备选） |

三条核心心法（来自对 [OpenAI showcase](https://developers.openai.com/showcase) 与官方 [imagegen demo](https://github.com/openai/openai-imagegen-demo) 的调研）：

1. **选对生成路径**——要"感觉"用位图，要"精确"用矢量，要"立体"用建模
2. **用参考图锚定风格**——一致性靠挂 `--ref` 已成品，不靠复述提示词
3. **迭代精修而非一次到位**——showcase 里惊艳的作品都是 6 轮左右迭代的产物

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
- 可选：`pip3 install pillow`（开启黑底/透明/平铺程序化验收）
- 可选：`pip3 install trimesh numpy`（3D 首选引擎）

## 用法（也可以直接对 agent 说"来一张 XX 贴图"）

```bash
# 文生图：无缝贴图
python3 scripts/gen_image.py --prompt-file prompt.txt \
  --out texture.png --expect-size 1024x1024 --expect-tile

# 编辑模式：保持构图换色（迭代精修的基本形态）
python3 scripts/gen_image.py --edit v1.png \
  --instruction "Keep the exact composition. Change only the palette to warm amber." \
  --out v2.png

# 程序化矢量：游戏图标
python3 scripts/gen_svg.py --prompt-file brief.txt --out icon.svg --viewbox 512

# 3D：低模硬表面
python3 scripts/gen_model.py --spec spec.md --out model.glb --max-tris 1500
```

提示词模板库（12 个场景 + 官方风格迁移公式 + 迭代修订指令写法）见
[references/prompt_library.md](references/prompt_library.md)，建模规格模板见
[assets/model_spec_template.md](assets/model_spec_template.md)。

脚本内置程序化验收：尺寸、黑底四角、透明度、贴图接缝、SVG 结构、GLB magic，
`GEN_OK` 且各项 `OK` 才算过；生成失败自动重试并打印 codex 输出尾部辅助诊断。

## 实测参考

| 操作 | 耗时 | 结果 |
|---|---|---|
| SVG 六边形芯片图标 | ~112s | 35 个矢量元素，5KB，全部校验通过 |
| 512x512 特效精灵（文生图） | ~74s | 尺寸/黑底验收通过 |
| 编辑模式（青→琥珀换色） | ~3m22s | 构图保持，换色精准 |
| 3D 低模（trimesh 引擎） | ~100s/个 | 面数/AABB 达标 |
