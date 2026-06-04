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
import shutil
from datetime import datetime
from pathlib import Path

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


def organize(folder: Path, apply: bool, by_date: bool) -> None:
    if not folder.exists() or not folder.is_dir():
        print(f"❌ 找不到文件夹：{folder}")
        return

    # 收集要处理的文件：只取直接位于该文件夹里的文件，跳过隐藏文件和本脚本自己
    files = [
        p for p in folder.iterdir()
        if p.is_file() and not p.name.startswith(".") and p.resolve() != Path(__file__).resolve()
    ]

    if not files:
        print(f"📂 {folder} 里没有需要整理的文件。")
        return

    mode = "✅ 实际执行" if apply else "👀 预演模式（不会真的移动文件，确认后加 --apply 执行）"
    print(f"\n整理文件夹：{folder}")
    print(f"模式：{mode}")
    print(f"分类方式：{'按修改日期(年-月)' if by_date else '按文件类型'}")
    print("-" * 56)

    moved = 0
    summary: dict[str, int] = {}

    for f in files:
        if by_date:
            # 按文件最后修改时间，分到 "2026-06" 这样的文件夹
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            bucket = mtime.strftime("%Y-%m")
        else:
            bucket = category_for(f.suffix)

        dest_dir = folder / bucket
        dest = unique_destination(dest_dir, f.name)

        print(f"  {f.name}  →  {bucket}/{dest.name}")
        summary[bucket] = summary.get(bucket, 0) + 1

        if apply:
            dest_dir.mkdir(exist_ok=True)
            shutil.move(str(f), str(dest))
        moved += 1

    print("-" * 56)
    print("统计：" + "，".join(f"{k} {v} 个" for k, v in sorted(summary.items())))
    if apply:
        print(f"🎉 完成！共整理 {moved} 个文件。")
    else:
        print(f"以上是预演结果（共 {moved} 个文件）。确认无误后，加 --apply 真正执行。")


def main():
    parser = argparse.ArgumentParser(
        description="把文件夹里的文件按类型（或日期）自动分到子文件夹。默认只预演不动文件。"
    )
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
    args = parser.parse_args()

    organize(Path(args.folder).expanduser(), apply=args.apply, by_date=args.by_date)


if __name__ == "__main__":
    main()
