# 贴图提示词库（生成时按场景取用）

## 总原则

- 完整英文提示词，一段式，材质、风格、技术要求全部写进文本。
- 尺寸写在提示词末尾（codex 会遵守），贴图常用 `1024x1024`。
- **说清"保持什么"和说清"改什么"同样重要**——编辑/派生场景漏写
  保持子句，模型会顺手重画纹理布局。这是 OpenAI 官方 demo（photobooth）
  提示词的核心手法。
- 多张贴图共享同一段风格锚点（相同的底色区间与点缀光色 + 质感关键词），
  否则同组观感会漂移；更稳的做法是给每张都挂 `--ref 组内定稿.png`。
- 模板里的 `<...>` 是待填槽位：风格锚点填你自己项目的，全组复用同一段。

## 无缝 albedo 贴图（文生图）——关键是 `seamless tileable` 与 `flat lighting`

```
Seamless tileable PBR albedo texture, <材质描述：如 dark metal plating
with interlocking panels / mossy stone bricks / weathered wood planks>,
<底色描述>, <点缀光色(色值)及分布，如 subtle emissive traces along seams>,
<细节特征：scratches / dirt / moss / wear>, top-down orthographic flat
lighting, no shadows, no vignette, uniform detail distribution, no borders,
no frame, game-ready texture, 1024x1024
```

接缝 FAIL 补丁：追加 `seamless top-bottom and left-right wraparound,
pattern must align at tile edges` 后重新生成；仍不过就 `--edit` 该图追加
`remove visible seams at tile edges, keep everything else identical`。

有机/天然材质（岩石、皮肤、泥土）再加一句 `no repeating obvious motifs,
organic irregular variation`，否则平铺后能看出图样重复。

## PBR 通道图派生（编辑模式，`--edit albedo.png`）

同一套材质的通道图必须从**同一张 albedo** 派生才能像素对齐：

**Normal map**

```
Convert this albedo texture into the matching tangent-space normal map:
raised areas where the albedo shows panel seams and bolts, recessed grooves
and scratches, mostly flat low-frequency surfaces, neutral blue-purple
encoding (#8080FF base), pixel-aligned with the source, no color information
from the original, 1024x1024
```

**Roughness map**

```
Convert this albedo texture into the matching roughness map (grayscale):
rough where the albedo shows matte and worn areas, smoother where it appears
polished or metallic, pixel-aligned with the source, no colors, 1024x1024
```

**Metallic map**（同理，灰度：金属部件白、非金属黑，占位填项目实际）

```
Convert this albedo texture into the matching metallic map (grayscale):
white where the material is bare metal, black where it is dielectric/painted,
follow the material regions in the source, pixel-aligned, 1024x1024
```

调色/改风格后的 albedo 版本变化时，通道图从**新版 albedo 重新派生**。

## 照片转贴图（编辑模式，`--edit photo.png`）

把手头的材质照片/扫描变成可用贴图：

```
Transform this photo into a seamless tileable PBR albedo texture: remove the
perspective distortion and uneven lighting, even out exposure to flat neutral
lighting, keep the true material colors and surface details, extend the
pattern naturally so it wraps seamlessly top-bottom and left-right, no
objects, no shadows from the original photo, 1024x1024
```

## 贴图风格迁移（编辑模式）

换材质风格但保持布局对齐（如把砖墙换成金属板墙面、同一套 UI 面板换配色）：

```
Transform this texture into <目标材质描述>：keep the exact panel layout,
seam positions and scale, replace the surface material and palette with
<风格锚点：质感关键词 + 底色 + 点缀光色(色值)>. Output requirements:
seamless tileable, same resolution, 1024x1024
```

通用四段公式（官方 demo 手法）：

```
<转换动词> this texture <目标效果>.
<具体视觉词汇，2–4 个材质/光影术语>.
<保持子句> while preserving the exact layout, scale and tile alignment.
<输出要求> Output requirements: seamless tileable, <尺寸>.
```

转换动词三选一：**Transform**（材质级换皮）/ **Recreate**（重绘但贴布局）/
**Reinterpret**（自由度最大的重新演绎）。

## 迭代修订指令写法

每轮只改**一个维度**，先说保持、再说修改。反例（一次改五件事，模型会
顾此失彼）："make it cleaner, add scratches, change color, more contrast, bigger bricks"。

正例：

```
Keep the exact layout, scale, palette and lighting. Change only the wear:
add more scratches and edge chipping concentrated near panel borders.
```

常用修订方向词：readability（纹理在大面积平铺下的可读性）、palette
（配色微调）、detail density（细节密度）、wear/aging（做旧程度）、
seam（接缝修复）。
