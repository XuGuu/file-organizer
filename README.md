# 🗂 文件整理工具 File Organizer

[![测试](https://github.com/XuGuu/file-organizer/actions/workflows/test.yml/badge.svg)](https://github.com/XuGuu/file-organizer/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个小巧的命令行工具，把乱糟糟的文件夹（默认是「下载」文件夹）里的文件，
按类型自动分到子文件夹：图片、文档、视频、音频、压缩包、安装包、代码、其他。

## ✨ 特点

- 🛡 **默认「预演模式」**：只打印会怎么整理、不真的动文件。确认无误后再加 `--apply` 真正执行——安全，不怕误操作。
- 🔁 **不覆盖**：遇到重名文件自动改名（`photo.jpg` → `photo_1.jpg`）。
- 📁 **只整理文件**，不动已有的子文件夹，跳过隐藏文件。
- 🚫 **不联网、不删除**任何文件，只是把文件「搬家」分类。
- 📅 还能按 `--by-date` 按「年-月」整理。

## 🚀 使用

需要电脑装了 Python 3（macOS 一般自带）。在终端里运行：

```bash
# 预演整理「下载」文件夹（只看不动，强烈建议先跑这个）
python3 organize.py

# 确认没问题后，真正执行
python3 organize.py --apply

# 整理指定文件夹（比如桌面）
python3 organize.py ~/Desktop --apply

# 按「年-月」分类，而不是按类型
python3 organize.py --by-date --apply

# 一键撤销最近一次整理（万一分错了，秒回原样）
python3 organize.py --revert

# 保留指定文件不动（支持通配符）
python3 organize.py --keep "*.tmp" --keep "重要*.pdf" --apply

# 递归整理子文件夹（自动避免循环）
python3 organize.py --depth 1 --apply

# 简洁模式（移动大量文件不刷屏）
python3 organize.py --quiet --apply
```

## 🆕 支持的分类

图片、文档、电子书、视频、音频、字体、设计稿、压缩包、安装包、代码、种子、其他。
想加新类型？打开 `organize.py`，在最上面的 `CATEGORIES` 字典里加扩展名即可。

## 📺 运行效果示例

```
整理文件夹：/Users/you/Downloads
模式：👀 预演模式（不会真的移动文件，确认后加 --apply 执行）
分类方式：按文件类型
--------------------------------------------------------
  photo.jpg  →  图片/photo.jpg
  report.pdf  →  文档/report.pdf
  song.mp3  →  音频/song.mp3
  ...
--------------------------------------------------------
统计：图片 1 个，文档 1 个，音频 1 个 ...
以上是预演结果。确认无误后，加 --apply 真正执行。
```

## 🛠 技术说明（给好奇的你）

- 用 Python 标准库 `pathlib` 和 `shutil`，无需安装任何第三方包。
- 想增加新的文件类型？打开 `organize.py`，在最上面的 `CATEGORIES` 字典里加扩展名即可。
- 安全设计：预演模式是默认行为，必须显式加 `--apply` 才会真正移动文件。

## 🧪 跑测试

```bash
python3 -m unittest test_organize.py -v
```

GitHub Actions 会在每次 push 自动跑测试，结果显示在仓库顶部的徽章里。

## 📜 更新日志

详见 [CHANGELOG.md](CHANGELOG.md)。

## 📄 许可证

MIT
