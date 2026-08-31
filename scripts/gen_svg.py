#!/usr/bin/env python3
"""codex 程序化矢量生成调用器——让 codex 直接写 SVG 文件。

适用：UI 图标/图标集、logo、简单扁平插画、九宫格边框、示意图。
相比位图生成的优势：任意缩放不糊、色值精确（品牌色可硬编码）、
体积小、生成后可用文本编辑器/代码继续改。

用法：
  python3 gen_svg.py --prompt "..." --out icon.svg [--viewbox 512]
  python3 gen_svg.py --prompt-file p.txt --out logo.svg

校验：XML 可解析、根为 <svg>、有 viewBox、含矢量图形元素、
无位图嵌入（<image>）与外部引用。
退出码：0 成功 / 2 codex 未安装 / 3 未登录 / 4 生成失败 / 5 校验不达标
"""
import argparse
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def find_codex() -> str:
    env = os.environ.get("CODEX_BIN")
    if env and Path(env).expanduser().exists():
        return str(Path(env).expanduser())
    for name in ("codex", "codex.cmd", "codex.exe"):
        p = shutil.which(name)
        if p:
            return p
    for cand in ("~/.local/bin/codex", "/usr/local/bin/codex", "/opt/homebrew/bin/codex"):
        p = os.path.expanduser(cand)
        if os.path.exists(p):
            return p
    return ""


DRAW_TAGS = {"path", "circle", "ellipse", "rect", "polygon", "polyline", "line"}


def svg_ok(path: str, viewbox: int):
    """返回 (ok, 报告行列表)。"""
    reports = []
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        return False, [f"xml-parse: FAIL ({e})"]
    reports.append("xml-parse: OK")
    good = True
    tag = root.tag.rsplit("}", 1)[-1]
    vb = root.get("viewBox", "")
    reports.append(f"root <{tag}> viewBox='{vb}': "
                   + ("OK" if tag == "svg" and vb else "FAIL"))
    good = good and tag == "svg" and bool(vb)
    if viewbox:
        want = f"0 0 {viewbox} {viewbox}"
        match = vb.replace("  ", " ") == want
        reports.append(f"viewbox-match {want}: {'OK' if match else 'FAIL'}")
        good = good and match
    shapes = sum(1 for el in root.iter() if el.tag.rsplit("}", 1)[-1] in DRAW_TAGS)
    reports.append(f"vector shapes={shapes}: " + ("OK" if shapes > 0 else "FAIL"))
    good = good and shapes > 0
    rasters = sum(1 for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "image")
    reports.append(f"embedded raster <image>: {'FAIL' if rasters else 'none OK'}")
    good = good and rasters == 0
    size = Path(path).stat().st_size
    reports.append(f"file size: {size // 1024} KB " + ("OK" if size < 512 * 1024 else "WARN (偏大)"))
    return good, reports


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="")
    ap.add_argument("--prompt-file", default="")
    ap.add_argument("--out", required=True, help="输出 SVG 路径")
    ap.add_argument("--viewbox", type=int, default=0,
                    help="要求正方形画布 viewBox='0 0 N N'，如 512")
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    prompt = args.prompt or (Path(args.prompt_file).read_text(encoding="utf-8") if args.prompt_file else "")
    if not prompt.strip():
        print("GEN_FAIL: empty prompt")
        sys.exit(4)

    codex = find_codex()
    if not codex:
        print("GEN_FAIL: codex CLI not found")
        print("install: mac `brew install codex` / all-platform `npm i -g @openai/codex`")
        sys.exit(2)
    try:
        r = subprocess.run([codex, "login", "status"], capture_output=True, text=True, timeout=60)
        if r.returncode != 0 or "Logged in" not in (r.stdout + r.stderr):
            print("GEN_FAIL: codex not logged in — run `codex login` once, then retry")
            sys.exit(3)
    except subprocess.TimeoutExpired:
        pass  # 预检超时不阻断，交给生成调用报错

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    vb_note = f' viewBox="0 0 {args.viewbox} {args.viewbox}" (exact).' if args.viewbox else " (choose a sensible viewBox)."
    full = (
        "Write ONE hand-crafted SVG file that satisfies this brief:\n\n"
        f"{prompt.strip()}\n\n"
        "Hard constraints:\n"
        f"- Root <svg> with xmlns and{vb_note}\n"
        "- Pure vector only: path/circle/ellipse/rect/polygon/line, gradients, "
        "filters allowed. NO <image>, no external hrefs, no scripts.\n"
        "- Use explicit fill colors (hex) as the brief specifies.\n"
        f"- Save it at {out_path} (overwrite if exists).\n"
        "Reply with only the file path when done."
    )

    try:
        r = subprocess.run(
            [codex, "exec", "--skip-git-repo-check", "-s", "workspace-write", full],
            capture_output=True, text=True, timeout=args.timeout, cwd=str(out_path.parent))
    except subprocess.TimeoutExpired:
        print(f"GEN_FAIL: codex exec timeout ({args.timeout}s)")
        sys.exit(4)

    if not out_path.exists():
        print("GEN_FAIL: output SVG not created")
        tail = ((r.stdout or "") + (r.stderr or "")) if r else ""
        if tail.strip():
            print("--- codex output tail ---")
            print("\n".join(tail.strip().splitlines()[-25:]))
        sys.exit(4)

    ok, reports = svg_ok(str(out_path), args.viewbox)
    print(f"GEN_OK: {out_path}")
    for line in reports:
        print(line)
    sys.exit(0 if ok else 5)


if __name__ == "__main__":
    main()
