#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件夹整理工具 (File Organizer)
================================
把一个乱糟糟的文件夹（默认是"下载"文件夹）里的文件，按类型自动分到子文件夹里：
图片、文档、视频、音频、压缩包、程序安装包、代码、其他。

特点：
- 默认"预演模式"（dry-run）：只打印会怎么移动，不真的动文件，安全。确认没问题再加 --apply 真正执行。
- 遇到重名文件会自动改名（加 _1、_2…），不会覆盖你的东西。
- 只整理文件，不动子文件夹。
- 不联网、不删除任何文件，只是"搬家"。

用法示例：
    python3 organize.py                      # 预演整理"下载"文件夹（只看不动）
    python3 organize.py --apply              # 真正整理"下载"文件夹
    python3 organize.py ~/Desktop            # 预演整理桌面
    python3 organize.py ~/Desktop --apply    # 真正整理桌面
    python3 organize.py --by-date            # 按"年-月"分文件夹，而不是按类型
"""

import argparse
import fnmatch
import json
import shutil
from datetime import datetime
from pathlib import Path

__version__ = "1.2.0"

# 这些名字是 organize 自己生成的分类文件夹，递归时要跳过，否则会循环嵌套
RESERVED_FOLDERS = {"图片", "文档", "电子书", "视频", "音频", "字体", "设计",
                    "压缩包", "安装包", "代码", "种子", "其他"}

# 每次实际执行整理后，把"原路径 → 新路径"的对应关系记录到这里。
# --revert 时读这个日志，把每个文件搬回去。
LOG_FILENAME = ".organize_log.json"

# ---------------------------------------------------------------------------
# 扩展名 → 分类。想加新类型，直接往这里加就行。
# ---------------------------------------------------------------------------
CATEGORIES = {
    "图片": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".svg", ".tiff", ".raw", ".cr2", ".nef"],
    "文档": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
             ".txt", ".md", ".csv", ".rtf", ".odt", ".pages", ".key", ".numbers"],
    "电子书": [".epub", ".mobi", ".azw", ".azw3", ".djvu", ".fb2"],
    "视频": [".mp4", ".mov", ".avi", ".mkv", ".flv", ".wmv", ".webm", ".m4v"],
    "音频": [".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma", ".opus"],
    "字体": [".ttf", ".otf", ".woff", ".woff2", ".eot"],
    "设计": [".psd", ".ai", ".sketch", ".fig", ".xd", ".indd"],
    "压缩包": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".dmg", ".iso"],
    "安装包": [".pkg", ".exe", ".msi", ".deb", ".rpm", ".app", ".apk"],
    "代码": [".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss", ".json", ".yaml", ".yml",
             ".java", ".c", ".cpp", ".h", ".go", ".rs", ".rb", ".php", ".sh", ".sql", ".swift", ".kt"],
    "种子": [".torrent"],
}
OTHER_FOLDER = "其他"  # 没匹配到的文件丢这里


def category_for(suffix: str) -> str:
    """根据扩展名返回分类名（找不到就归入'其他'）。"""
    suffix = suffix.lower()
    for name, exts in CATEGORIES.items():
        if suffix in exts:
            return name
    return OTHER_FOLDER


def unique_destination(dest_dir: Path, filename: str) -> Path:
    """如果目标文件夹里已有同名文件，自动在文件名后加 _1、_2… 避免覆盖。"""
    target = dest_dir / filename
    if not target.exists():
        return target
    stem, suffix = Path(filename).stem, Path(filename).suffix
    i = 1
    while True:
        candidate = dest_dir / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def collect_files(folder: Path, depth: int) -> list[Path]:
    """收集文件。depth=0 表示只取 folder 顶层；depth=1 多扫一层子文件夹；以此类推。
    跳过隐藏文件、本脚本、以及上次整理生成的分类文件夹（防止重复嵌套）。"""
    me = Path(__file__).resolve()
    files: list[Path] = []

    def walk(d: Path, remaining: int):
        for p in d.iterdir():
            if p.name.startswith("."):       # 隐藏文件 / 文件夹一律跳过
                continue
            if p.is_file():
                if p.resolve() != me:
                    files.append(p)
            elif p.is_dir() and remaining > 0 and p.name not in RESERVED_FOLDERS:
                walk(p, remaining - 1)

    walk(folder, depth)
    return files


def organize(folder: Path, apply: bool, by_date: bool, keep_patterns: list[str] | None = None,
             quiet: bool = False, depth: int = 0) -> None:
    if not folder.exists():
        print(f"❌ 路径不存在：{folder}")
        print("    检查一下拼写，或换个绝对路径试试（如 /Users/你的用户名/Downloads）。")
        return
    if folder.is_file():
        print(f"❌ 这是一个文件，不是文件夹：{folder}")
        print(f"    你大概想整理它所在的目录：{folder.parent}")
        return
    if not folder.is_dir():
        print(f"❌ 这不是一个普通文件夹：{folder}")
        return

    # 收集要处理的文件
    files = collect_files(folder, depth)

    # 按 --keep 模式排除（支持通配符，如 "*.tmp" 或 "重要*.pdf"）
    if keep_patterns:
        before = len(files)
        files = [f for f in files if not any(fnmatch.fnmatch(f.name, p) for p in keep_patterns)]
        skipped = before - len(files)
        if skipped:
            print(f"（按 --keep 跳过了 {skipped} 个文件）")

    if not files:
        print(f"📂 {folder} 里没有需要整理的文件。")
        return

    mode = "✅ 实际执行" if apply else "👀 预演模式（不会真的移动文件，确认后加 --apply 执行）"
    if not quiet:
        print(f"\n整理文件夹：{folder}")
        print(f"模式：{mode}")
        print(f"分类方式：{'按修改日期(年-月)' if by_date else '按文件类型'}")
        print("-" * 56)

    moved = 0
    summary: dict[str, int] = {}
    operations: list[tuple[str, str]] = []  # 真正执行时，记录 (原路径, 新路径)

    for f in files:
        if by_date:
            # 按文件最后修改时间，分到 "2026-06" 这样的文件夹
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            bucket = mtime.strftime("%Y-%m")
        else:
            bucket = category_for(f.suffix)

        dest_dir = folder / bucket
        dest = unique_destination(dest_dir, f.name)

        if not quiet:
            print(f"  {f.name}  →  {bucket}/{dest.name}")
        summary[bucket] = summary.get(bucket, 0) + 1

        if apply:
            dest_dir.mkdir(exist_ok=True)
            shutil.move(str(f), str(dest))
            operations.append((str(f), str(dest)))
        moved += 1

    if not quiet:
        print("-" * 56)
    print("统计：" + "，".join(f"{k} {v} 个" for k, v in sorted(summary.items())))
    if apply:
        # 把这一次操作记下来，方便 --revert 撤销
        log_path = folder / LOG_FILENAME
        log_data = {"at": datetime.now().isoformat(timespec="seconds"), "ops": operations}
        log_path.write_text(json.dumps(log_data, ensure_ascii=False, indent=2))
        print(f"🎉 完成！共整理 {moved} 个文件。")
        print(f"💡 如需撤销：python3 organize.py {folder} --revert")
    else:
        print(f"以上是预演结果（共 {moved} 个文件）。确认无误后，加 --apply 真正执行。")


def revert(folder: Path) -> None:
    """读取上次整理的日志，把文件搬回原路径。"""
    log_path = folder / LOG_FILENAME
    if not log_path.exists():
        print(f"❌ 找不到操作日志：{log_path}")
        print("    （只能撤销最近一次用 --apply 整理过的文件夹。）")
        return
    log_data = json.loads(log_path.read_text())
    ops = log_data.get("ops", [])
    if not ops:
        print("日志里没有可撤销的操作。")
        return

    print(f"\n准备撤销 {len(ops)} 个文件的移动（来自 {log_data.get('at', '?')}）：")
    print("-" * 56)
    restored, missing = 0, 0
    for original, current in ops:
        cur_path = Path(current)
        orig_path = Path(original)
        if not cur_path.exists():
            print(f"  ⚠ 已不在原位置，跳过：{cur_path.name}")
            missing += 1
            continue
        # 如果原路径有同名文件了，加 _restored 后缀，避免覆盖
        if orig_path.exists():
            orig_path = orig_path.with_name(orig_path.stem + "_restored" + orig_path.suffix)
        orig_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(cur_path), str(orig_path))
        print(f"  {cur_path.name}  ←  {orig_path}")
        restored += 1
    print("-" * 56)
    print(f"✅ 已撤销 {restored} 个文件；{missing} 个文件已不在原位置无法处理。")
    log_path.unlink()  # 日志用完就删，避免重复撤销


def main():
    parser = argparse.ArgumentParser(
        description="把文件夹里的文件按类型（或日期）自动分到子文件夹。默认只预演不动文件。"
    )
    parser.add_argument("--version", action="version", version=f"organize.py {__version__}")
    parser.add_argument(
        "folder", nargs="?", default=str(Path.home() / "Downloads"),
        help="要整理的文件夹路径（默认：你的'下载'文件夹 ~/Downloads）",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="真正执行移动（不加这个参数则只预演、不动文件）",
    )
    parser.add_argument(
        "--by-date", action="store_true",
        help="按文件修改日期(年-月)分类，而不是按文件类型",
    )
    parser.add_argument(
        "--revert", action="store_true",
        help="撤销该文件夹最近一次整理（读取 .organize_log.json 还原）",
    )
    parser.add_argument(
        "--keep", action="append", metavar="PATTERN", default=[],
        help="保留匹配此模式的文件不动，支持通配符。可多次使用，如 --keep '*.tmp' --keep 'README.md'",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="简洁模式：只打印统计结果，不逐条列出每个文件（移动文件多时清爽很多）",
    )
    parser.add_argument(
        "--depth", type=int, default=0, metavar="N",
        help="递归深度：0=只整理顶层（默认），1=多扫一层子文件夹，依此类推。会跳过已有的分类文件夹避免循环。",
    )
    args = parser.parse_args()

    folder = Path(args.folder).expanduser()
    if args.revert:
        revert(folder)
    else:
        organize(folder, apply=args.apply, by_date=args.by_date,
                 keep_patterns=args.keep, quiet=args.quiet, depth=args.depth)


if __name__ == "__main__":
    main()
