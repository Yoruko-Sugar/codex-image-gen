#!/usr/bin/env python3
"""codex 程序化建模调用器（mac/win 跨平台）。

用法：
  python3 gen_model.py --spec /path/spec.md --out /path/model.glb [--max-tris 1500]
                       [--engine auto|python|blender]

引擎：python=纯 trimesh 建模（默认优先，无 Blender、零崩溃弹窗）；
blender=Blender headless；auto=trimesh 可用则 python，否则 blender。
前置：codex CLI 已登录；python 引擎需 `pip3 install trimesh numpy`，
blender 引擎需本机 Blender。
退出码：0 成功 / 2 codex 缺失 / 3 未登录 / 4 建模后端缺失 / 5 生成失败
"""
import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path


def find_codex() -> str:
    for name in ("codex", "codex.cmd", "codex.exe"):
        p = shutil.which(name)
        if p:
            return p
    for cand in ("~/.local/bin/codex", "/usr/local/bin/codex", "/opt/homebrew/bin/codex"):
        p = os.path.expanduser(cand)
        if os.path.exists(p):
            return p
    return ""


def find_blender() -> str:
    p = shutil.which("blender")
    if p:
        return p
    for cand in ("/Applications/Blender.app/Contents/MacOS/Blender",
                 "C:/Program Files/Blender Foundation/Blender/blender.exe"):
        c = os.path.expanduser(cand)
        if os.path.exists(c):
            return c
    return ""


def glb_ok(path: str):
    """校验 GLB magic 与 JSON chunk 可解析，返回 (True, 摘要) 或 (False, 原因)。"""
    try:
        with open(path, "rb") as f:
            head = f.read(12)
            if head[:4] != b"glTF" or head[4:8] != b"\x02\x00\x00\x00":
                return False, "bad GLB magic/version"
            jlen, jtype = struct.unpack("<II", f.read(8))
            if jtype != 0x4E4F534A:
                return False, "missing JSON chunk"
            data = json.loads(f.read(jlen).decode("utf-8", "ignore"))
        n_meshes = len(data.get("meshes", []))
        n_mats = len(data.get("materials", []))
        return True, f"meshes={n_meshes} materials={n_mats}"
    except Exception as e:
        return False, str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True, help="建模规格 markdown 文件")
    ap.add_argument("--out", required=True, help="输出 GLB 绝对路径")
    ap.add_argument("--max-tris", type=int, default=1500)
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--engine", choices=["auto", "python", "blender"], default="auto")
    args = ap.parse_args()

    spec_path = Path(args.spec).expanduser().resolve()
    if not spec_path.exists():
        print(f"GEN_FAIL: spec not found: {spec_path}")
        sys.exit(5)

    codex = find_codex()
    if not codex:
        print("GEN_FAIL: codex CLI not found")
        print("install: mac `brew install codex` / all-platform `npm i -g @openai/codex`")
        sys.exit(2)
    r = subprocess.run([codex, "login", "status"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0 or "Logged in" not in (r.stdout + r.stderr):
        print("GEN_FAIL: codex not logged in — run `codex login` once, then retry")
        sys.exit(3)

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    name = out_path.stem
    build_py = out_path.parent / f"build_{name}.py"

    # 引擎选择：trimesh 纯 python（首选）或 Blender headless
    has_trimesh = False
    try:
        import importlib.util
        has_trimesh = importlib.util.find_spec("trimesh") is not None
    except Exception:
        pass
    engine = args.engine
    if engine == "auto":
        engine = "python" if has_trimesh else "blender"
    if engine == "python" and not has_trimesh:
        print("GEN_FAIL: trimesh not installed (pip3 install trimesh numpy)")
        sys.exit(4)

    if engine == "python":
        prompt = f"""Read the modeling spec at {spec_path}. Then:
1. Write a pure Python script at {build_py} (NO Blender, NO bpy) using the trimesh
   library to build the model exactly per spec. Compose primitives
   (trimesh.creation.box/cylinder/cone/sphere + transforms; boolean union where helpful).
   Materials: PBRMaterial with plain baseColorFactor and emissiveFactor, no textures.
   Build a trimesh.Scene with one named geometry per material and export via
   scene.export({out_path}) (GLB, glTF 2.0, Y-up, meters).
   Hard constraints: {args.max_tris} triangles max total.
2. Run it with python3; fix and rerun until it exports successfully.
3. Verify {out_path} exists. Report: total triangle count, bounding box size,
   number of geometries/materials, origin height.
Reply with only those verification numbers when done."""
    else:
        blender = find_blender()
        if not blender:
            print("GEN_FAIL: blender not found")
            print("install: mac `brew install --cask blender` / win installer from blender.org")
            sys.exit(4)
        prompt = f"""Read the modeling spec at {spec_path}. Then:
1. Write a Blender Python script at {build_py} that builds the model exactly per spec
   (hard constraints: glTF 2.0 GLB export, Y-up, meters, {args.max_tris} triangles max total,
   plain-color material slots, no textures).
2. Run it headless: "{blender}" --background --python {build_py}
   (the script itself must export {out_path} via bpy.ops.export_scene.gltf).
3. Verify {out_path} exists. Report: total triangle count, bounding box size,
   number of material slots, origin height.
Reply with only those verification numbers when done."""

    t0 = time.time()
    try:
        subprocess.run(
            [codex, "exec", "--skip-git-repo-check", "-s", "workspace-write", prompt],
            capture_output=True, text=True, timeout=args.timeout, cwd=str(out_path.parent))
    except subprocess.TimeoutExpired:
        print(f"GEN_FAIL: codex exec timeout ({args.timeout}s)")
        sys.exit(5)

    if not out_path.exists():
        print("GEN_FAIL: output GLB not created")
        sys.exit(5)
    ok, info = glb_ok(str(out_path))
    if not ok:
        print(f"GEN_FAIL: invalid GLB ({info})")
        sys.exit(5)
    print(f"GEN_OK: {out_path} ({out_path.stat().st_size // 1024} KB, {time.time()-t0:.0f}s, engine={engine})")
    print(f"glb: {info}")
    print(f"build script kept: {build_py}")


if __name__ == "__main__":
    main()
