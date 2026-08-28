#!/usr/bin/env python3
"""codex 生图调用器（mac/win 跨平台）。

三种模式：
  # 1. 文生图
  python3 gen_image.py --prompt-file p.txt --out out.png --expect-size 1024x1024
  # 2. 参考图生成（风格/主体锚定，可多张；经 codex exec -i 附图）
  python3 gen_image.py --prompt-file p.txt --ref style.png --ref subject.png --out out.png
  # 3. 编辑模式（改造现有图：风格迁移 / 局部修改 / 迭代精修）
  python3 gen_image.py --edit src.png --instruction "make the rim glow amber" --out out.png
     （长指令用 --instruction-file i.txt）

验收开关：--expect-size WxH / --expect-black-bg / --expect-tile / --expect-alpha
生成失败自动重试一次；仍失败时打印 codex 输出尾部辅助诊断。

退出码：0 成功 / 2 codex 未安装 / 3 未登录 / 4 生成失败 / 5 验收不达标
"""
import argparse
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path


def find_codex() -> str:
    env = os.environ.get("CODEX_BIN")
    if env and Path(env).expanduser().exists():
        return str(Path(env).expanduser())
    for name in ("codex", "codex.cmd", "codex.exe"):
        p = shutil.which(name)
        if p:
            return p
    # mac 常见手动安装位
    for cand in ("~/.local/bin/codex", "/usr/local/bin/codex", "/opt/homebrew/bin/codex"):
        p = os.path.expanduser(cand)
        if os.path.exists(p):
            return p
    return ""


def png_size(path: str):
    with open(path, "rb") as f:
        head = f.read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w, h = struct.unpack(">II", head[16:24])
    return int(w), int(h)


def check_pil(kind: str, path: str) -> str:
    try:
        from PIL import Image
    except ImportError:
        return f"{kind}: SKIP (no PIL)"
    im = Image.open(path)
    if kind == "black-bg":
        rgb = im.convert("RGB")
        w, h = rgb.size
        corners = [rgb.getpixel(p) for p in [(4, 4), (w - 5, 4), (4, h - 5), (w - 5, h - 5)]]
        m = sum(sum(c) for c in corners) / 12
        return f"black-bg corner={m:.0f} {'OK' if m < 20 else 'FAIL'}"
    if kind == "alpha":
        if im.mode not in ("RGBA", "LA", "PA"):
            return "alpha: FAIL (image has no alpha channel)"
        a = im.convert("RGBA")
        w, h = a.size
        corners = [a.getpixel(p)[3] for p in [(4, 4), (w - 5, 4), (4, h - 5), (w - 5, h - 5)]]
        m = sum(corners) / 4
        return f"alpha corner={m:.0f} {'OK' if m < 20 else 'FAIL'}"
    if kind == "tile":
        px = list(im.convert("RGB").getdata())
        w, h = im.size
        lr = sum(abs(px[i * w][c] - px[i * w + w - 1][c]) for i in range(0, h, 16) for c in range(3)) / (h / 16 * 3)
        tb = sum(abs(px[i][c] - px[(h - 1) * w + i][c]) for i in range(0, w, 16) for c in range(3)) / (w / 16 * 3)
        return f"tile LR={lr:.0f} TB={tb:.0f} {'OK' if max(lr, tb) < 25 else 'FAIL'}"
    return "?"


def build_prompt(args, prompt: str, out_path: Path) -> str:
    """按模式拼装给 codex 的完整指令。"""
    size_note = f"Target dimensions {args.expect_size}. " if args.expect_size else ""
    if args.edit:
        # 编辑模式：官方风格迁移公式 = 转换指令 + 保持子句 + 输出要求
        return (
            "Transform the attached image (the only attached input image) as follows:\n\n"
            f"{prompt.strip()}\n\n"
            "Output requirements: preserve everything not explicitly changed "
            "(identity, pose, composition, framing, scene layout). "
            f"{size_note}"
            f"Save the result as {out_path} (overwrite if exists). "
            "Reply with only the file path when done."
        )
    ref_note = ""
    if args.ref:
        ref_note = (
            "The attached image(s) are visual conditioning for the generation "
            "(style/subject anchors — follow how the prompt says to use them).\n\n"
        )
    return (
        f"{ref_note}"
        "Use your built-in image generation tool to create ONE image with this exact prompt:\n\n"
        f"{prompt.strip()}\n\n"
        f"{size_note}"
        f"Save the generated image as {out_path} (overwrite if exists). "
        "Reply with only the file path when done."
    )


def read_text_arg(value: str, file_value: str, what: str) -> str:
    text = value or (Path(file_value).read_text(encoding="utf-8") if file_value else "")
    if not text.strip():
        print(f"GEN_FAIL: empty {what}")
        sys.exit(4)
    return text.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="")
    ap.add_argument("--prompt-file", default="")
    ap.add_argument("--ref", action="append", default=[],
                    help="参考图路径，可重复；经 codex -i 附图（风格/主体锚定）")
    ap.add_argument("--edit", default="", help="编辑模式的源图路径（改造现有图）")
    ap.add_argument("--instruction", default="", help="编辑模式的转换指令")
    ap.add_argument("--instruction-file", default="")
    ap.add_argument("--out", required=True, help="输出 PNG 绝对或相对路径")
    ap.add_argument("--expect-size", default="", help="如 512x512")
    ap.add_argument("--expect-black-bg", action="store_true")
    ap.add_argument("--expect-tile", action="store_true")
    ap.add_argument("--expect-alpha", action="store_true",
                    help="要求四角透明（透明底精灵/图标）")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--retries", type=int, default=1, help="生成失败后的自动重试次数")
    args = ap.parse_args()

    if args.edit:
        prompt = read_text_arg(args.instruction, args.instruction_file, "instruction")
    else:
        prompt = read_text_arg(args.prompt, args.prompt_file, "prompt")

    for r in args.ref:
        if not Path(r).expanduser().exists():
            print(f"GEN_FAIL: ref image not found: {r}")
            sys.exit(4)
    if args.edit and not Path(args.edit).expanduser().exists():
        print(f"GEN_FAIL: edit source not found: {args.edit}")
        sys.exit(4)

    codex = find_codex()
    if not codex:
        print("GEN_FAIL: codex CLI not found")
        print("install: mac `brew install codex` / all-platform `npm i -g @openai/codex`")
        print("已安装但找不到时可用环境变量 CODEX_BIN 指定路径")
        sys.exit(2)

    # 登录预检（失败不阻断生成尝试，但给出指引）
    try:
        r = subprocess.run([codex, "login", "status"], capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        r = None
    if r is None or r.returncode != 0 or "Logged in" not in (r.stdout + r.stderr):
        print("GEN_FAIL: codex not logged in — run `codex login` once (browser OAuth), then retry")
        sys.exit(3)

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    full = build_prompt(args, prompt, out_path)

    cmd = [codex, "exec", "--skip-git-repo-check", "-s", "workspace-write"]
    attach = [Path(args.edit).expanduser().resolve()] if args.edit else \
             [Path(r).expanduser().resolve() for r in args.ref]
    for img in attach:
        cmd += ["-i", str(img)]
    # -i 是可变参数，会吞掉后续位置参数；-- 终止选项解析，保证 prompt 被当作位置参数
    cmd += ["--", full]

    # 生成 + 自动重试；失败时打印 codex 输出尾部
    attempts = 1 + max(0, args.retries)
    for attempt in range(1, attempts + 1):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=args.timeout, cwd=str(out_path.parent))
            tail = (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired as e:
            tail = e.output or ""
            if isinstance(tail, bytes):
                tail = tail.decode("utf-8", "ignore")
            tail += f"\n[codex exec timeout after {args.timeout}s]"
        if out_path.exists():
            break
        print(f"GEN_FAIL: output not created (attempt {attempt}/{attempts})")
        if tail.strip():
            print("--- codex output tail ---")
            print("\n".join(tail.strip().splitlines()[-25:]))
            print("--- end tail ---")
        if attempt < attempts:
            print("retrying...")
    else:
        sys.exit(4)

    ok = True
    size = png_size(str(out_path))
    print(f"GEN_OK: {out_path}")
    if size:
        print(f"size: {size[0]}x{size[1]}")
        if args.expect_size:
            want = tuple(int(x) for x in args.expect_size.lower().split("x"))
            good = size == want
            ok = ok and good
            print(f"expect-size {want[0]}x{want[1]}: {'OK' if good else 'FAIL'}")
    for flag, kind in ((args.expect_black_bg, "black-bg"),
                       (args.expect_alpha, "alpha"),
                       (args.expect_tile, "tile")):
        if flag:
            res = check_pil(kind, str(out_path))
            print(res)
            ok = ok and not res.endswith("FAIL")
    sys.exit(0 if ok else 5)


if __name__ == "__main__":
    main()
