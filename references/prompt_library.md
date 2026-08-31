# 提示词库（生成时按场景取用）

## 总原则

- 完整英文提示词，一段式，风格、主体、技术要求全部写进文本。
- 尺寸写在提示词末尾（codex 会遵守），如 `1024x1024`。
- **说清"保持什么"和说清"改什么"同样重要**——编辑/迁移场景漏写保持
  子句，模型就会顺手重画构图。这是 OpenAI 官方 demo（photobooth）提示词
  的核心手法。
- 多张同批素材共享同一段风格锚点（相同的底色区间与点缀光色），否则批次
  观感会漂移；更稳的做法是给每张都挂 `--ref 第一张成品.png`。
- 模板里的 `<...>` 是待填槽位：风格锚点（底色 + 点缀光色 + 质感关键词）
  填你自己项目的，全组素材复用同一段。

## 文生图模板

### 无缝贴图（材质/地面/皮肤）——关键是 `seamless tileable` 与 `flat lighting`

```
Seamless tileable PBR albedo texture, <材质描述：如 dark metal plating
with interlocking panels / mossy stone bricks>, <底色描述>, <点缀光色(色值)
及分布，如 subtle emissive traces along seams>, <细节特征：scratches /
dirt / wear>, top-down orthographic flat lighting, no shadows, no vignette,
uniform detail distribution, game-ready texture, 1024x1024
```

贴图 FAIL 补丁：追加 `seamless top-bottom and left-right wraparound,
pattern must align at tile edges` 后重新生成。

### 特效精灵（加法混合粒子）——关键是纯黑底与不贴边

```
Game VFX sprite, <单个特效描述：如 an expanding shockwave ring / a burst
of sparks>, <能量边缘与内部渐变描述>, <风格锚点：质感关键词 + 点缀色(色值)>,
isolated on pure black background, centered, effect does not touch edges, 512x512
```

### 透明底精灵/图标（角色、道具、UI 元素）

```
Game asset sprite of <主体>, <风格锚点：质感关键词 + 配色(色值)>,
<姿态/朝向描述>, isolated on fully transparent background, centered with
margin, crisp silhouette, no text, no watermark, 512x512
```

配 `--expect-alpha` 验收四角透明。

### UI 图标——关键是纯色底与居中

```
<主体描述，如 a hexagonal data-core chip with circuit lines>, <风格锚点：
flat game icon style + 底色(色值) + 点缀色(色值)>, centered composition,
solid dark background (<色值>), crisp edges, high contrast, no text, 512x512
```

### 关键视觉/标题画（title screen、宣传图）

```
Key art for a <项目类型> title screen, wide establishing shot of <主体场景>,
dramatic rim lighting, <风格锚点：质感 + 主色 + 点缀光色(色值)>,
atmospheric fog, cinematic composition with clear focal point and empty
<upper/one side> third for title text, highly detailed, 1536x1024
```

### 角色概念设定图（多视角参考）

```
Character concept sheet, <角色描述：职业/体型/装备/配色>, three views
(front / side / back) arranged in a horizontal row on neutral dark gray
background, consistent proportions and details across views, flat neutral
lighting, <风格锚点：concept art 风格关键词>, no text labels, 1536x1024
```

### 精灵序列帧（动画）

```
Sprite sheet of <主体与动画描述，如 walk cycle / propeller spinning>,
<N 帧> frames arranged in a single horizontal row, equal frame size, consistent
lighting and colors, <风格锚点>, plain dark background (<色值>),
frames evenly spaced, no text, 1536x256
```

序列帧生成后需程序化切帧（按等分裁剪），帧间闪烁多半是提示词里
"consistent lighting and colors" 没写或批次漂移。

### 场景背景/环境图（可含视差分层）

```
Game background environment, <场景描述>, <风格锚点：氛围 + 主色 + 点缀色(色值)>,
layered depth (foreground silhouettes / midground structures / background glow),
horizontal composition designed for parallax, no characters, no text, 1536x1024
```

### 九宫格 UI 边框

```
Game UI panel border frame, 9-slice layout: ornate corners, plain straight
edge segments, <风格锚点：质感 + 底色(色值) + 边缘光色(色值)>,
center area fully flat single color (<色值>), symmetrical, no text, 512x512
```

### PBR 通道图（在 albedo 成品基础上派生）

从已有 albedo 生成配套通道图时用**编辑模式**（`--edit albedo.png`）：

```
Convert this albedo texture into the matching tangent-space normal map:
raised areas where the albedo shows panel seams and bolts, recessed grooves
and scratches, mostly flat low-frequency surfaces, neutral blue-purple
encoding (#8080FF base), pixel-aligned with the source, no color information
from the original, 1024x1024
```

roughness / metallic 同理（灰度图）。同一套 UV 的通道图必须从同一张
albedo 派生才能对齐。

### 海报/封面

```
Poster for <项目名/主题>, <构图描述：主体+场景+氛围>, bold focal hierarchy,
<风格锚点：主色 + 点缀色(色值)>, clear space for headline typography,
print-ready composition, no embedded text (typography added later in code),
1024x1536
```

## 风格迁移/编辑公式（官方 demo 手法）

官方 Image API demo 的提示词结构，四段式，经过验证：

```
<转换动词> the attached image <风格转换目标>.
<具体视觉词汇，2–4 个材质/光影/线条术语>.
<保持子句> while preserving the same identity, pose, expression, framing,
and scene layout.
<输出要求> Output requirements: <尺寸/朝向等>.
```

转换动词三选一：**Transform**（材质级换皮）/ **Recreate**（重绘但贴构图）/
**Reinterpret**（自由度最大的重新演绎）。

六个官方风格的目标描述，可直接借用其视觉词汇：

| 风格 | 关键视觉词汇 |
|---|---|
| 针织玩偶 | soft knitted dolls, visible yarn, stitched fabric, embroidered details |
| 现代数字插画 | bold shapes, smooth vector-like forms, vivid colors, crisp edges |
| 水彩 | fluid brush strokes, soft pigment bleeding, delicate pastel depth |
| 电影动漫 | delicate linework, painterly shading, atmospheric lighting, soft gradients |
| 未来科幻 | cool blue palette, neon glows, holographic lighting, reflective surfaces |
| Lo-Fi 漫画 | bold outlines, simplified shading, muted retro colors, soft halftone |

编辑示例（把截图转成宣传图、给白模渲染图上材质）：

```
Recreate the attached screenshot as a polished marketing key art: same
composition and camera angle, add dramatic lighting, atmospheric fog and
cinematic color grading in <风格锚点：配色描述>. Output requirements:
1536x1024, keep every structural element in place.
```

## 迭代修订指令写法

每轮只改**一个维度**，先说保持、再说修改。反例（一次改五件事，模型会
顾此失彼）："make it cooler, add glow, change angle, more detail, different color"。

正例：

```
Keep the exact composition, subject pose, framing and color palette.
Change only the background: replace the plain wall with <新背景描述>.
```

常用修订方向词：readability（轮廓/对比度）、identity（主体特征是否走样）、
lighting（光影层次）、palette（配色微调）、detail density（细节密度）。
