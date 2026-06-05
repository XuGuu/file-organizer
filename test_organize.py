#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
file-organizer 的单元测试。

跑测试：
    python3 -m unittest test_organize.py -v
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# 把脚本目录加入 sys.path，方便直接 import 同目录的 organize 模块
sys.path.insert(0, str(Path(__file__).resolve().parent))

import organize  # noqa: E402


class TestCategoryFor(unittest.TestCase):
    """category_for(扩展名) → 应该返回正确的分类名。"""

    def test_known_image(self):
        self.assertEqual(organize.category_for(".jpg"), "图片")
        self.assertEqual(organize.category_for(".PNG"), "图片")  # 大小写不敏感

    def test_known_document(self):
        self.assertEqual(organize.category_for(".pdf"), "文档")
        self.assertEqual(organize.category_for(".md"), "文档")

    def test_known_audio(self):
        self.assertEqual(organize.category_for(".mp3"), "音频")
        self.assertEqual(organize.category_for(".opus"), "音频")

    def test_new_categories(self):
        # v1.1.0 新增的分类
        self.assertEqual(organize.category_for(".epub"), "电子书")
        self.assertEqual(organize.category_for(".ttf"), "字体")
        self.assertEqual(organize.category_for(".psd"), "设计")
        self.assertEqual(organize.category_for(".torrent"), "种子")

    def test_unknown_falls_to_other(self):
        self.assertEqual(organize.category_for(".xyz"), "其他")
        self.assertEqual(organize.category_for(".weirdext"), "其他")


class TestUniqueDestination(unittest.TestCase):
    """unique_destination：遇到重名应自动加 _1、_2 后缀避免覆盖。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_no_collision(self):
        # 目标不存在 → 直接返回原始路径
        dest = organize.unique_destination(self.tmp, "photo.jpg")
        self.assertEqual(dest, self.tmp / "photo.jpg")

    def test_with_collision(self):
        (self.tmp / "photo.jpg").touch()
        dest = organize.unique_destination(self.tmp, "photo.jpg")
        self.assertEqual(dest, self.tmp / "photo_1.jpg")

    def test_with_multiple_collisions(self):
        (self.tmp / "photo.jpg").touch()
        (self.tmp / "photo_1.jpg").touch()
        (self.tmp / "photo_2.jpg").touch()
        dest = organize.unique_destination(self.tmp, "photo.jpg")
        self.assertEqual(dest, self.tmp / "photo_3.jpg")


class TestOrganizeAndRevert(unittest.TestCase):
    """端到端：整理 → 撤销 应能完美还原。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        # 准备几个不同类型的文件
        (self.tmp / "a.jpg").write_text("img")
        (self.tmp / "b.pdf").write_text("doc")
        (self.tmp / "c.mp3").write_text("audio")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_dry_run_does_not_move(self):
        organize.organize(self.tmp, apply=False, by_date=False, quiet=True)
        # 顶层文件应仍在
        self.assertTrue((self.tmp / "a.jpg").exists())
        self.assertTrue((self.tmp / "b.pdf").exists())
        # 不应创建分类子目录
        self.assertFalse((self.tmp / "图片").exists())

    def test_apply_moves_files(self):
        organize.organize(self.tmp, apply=True, by_date=False, quiet=True)
        self.assertTrue((self.tmp / "图片" / "a.jpg").exists())
        self.assertTrue((self.tmp / "文档" / "b.pdf").exists())
        self.assertTrue((self.tmp / "音频" / "c.mp3").exists())
        # 顶层那几个原文件应已移走
        self.assertFalse((self.tmp / "a.jpg").exists())
        # 日志应已写入
        self.assertTrue((self.tmp / organize.LOG_FILENAME).exists())

    def test_revert_restores_files(self):
        organize.organize(self.tmp, apply=True, by_date=False, quiet=True)
        organize.revert(self.tmp)
        # 顶层文件应恢复
        self.assertTrue((self.tmp / "a.jpg").exists())
        self.assertTrue((self.tmp / "b.pdf").exists())
        self.assertTrue((self.tmp / "c.mp3").exists())
        # 日志应被清理掉，避免重复撤销
        self.assertFalse((self.tmp / organize.LOG_FILENAME).exists())

    def test_keep_pattern_skips_files(self):
        (self.tmp / "important.pdf").write_text("keep me")
        organize.organize(self.tmp, apply=True, by_date=False, quiet=True,
                          keep_patterns=["important.pdf"])
        # 被 --keep 命中的文件应仍在顶层
        self.assertTrue((self.tmp / "important.pdf").exists())
        # 其他文件正常分类
        self.assertTrue((self.tmp / "图片" / "a.jpg").exists())


class TestCollectFiles(unittest.TestCase):
    """collect_files：默认只取顶层；--depth N 多扫 N 层；自动跳过分类文件夹与隐藏文件。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "top.jpg").touch()
        (self.tmp / "sub").mkdir(); (self.tmp / "sub" / "in_sub.pdf").touch()
        (self.tmp / "sub" / "deeper").mkdir(); (self.tmp / "sub" / "deeper" / "deep.mp3").touch()
        (self.tmp / ".hidden.txt").touch()
        # 模拟「分类文件夹」（递归时应跳过，否则会循环）
        (self.tmp / "图片").mkdir(); (self.tmp / "图片" / "old.jpg").touch()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_depth_0_only_top_level(self):
        names = {p.name for p in organize.collect_files(self.tmp, depth=0)}
        self.assertEqual(names, {"top.jpg"})

    def test_depth_1_includes_one_subfolder(self):
        names = {p.name for p in organize.collect_files(self.tmp, depth=1)}
        self.assertEqual(names, {"top.jpg", "in_sub.pdf"})
        # 还没深到 deeper
        self.assertNotIn("deep.mp3", names)

    def test_depth_2_includes_deeper(self):
        names = {p.name for p in organize.collect_files(self.tmp, depth=2)}
        self.assertIn("deep.mp3", names)

    def test_skips_reserved_category_folders(self):
        # 即便 depth 很大，分类文件夹（如「图片」）里的旧文件也不应被收进来重新移动
        names = {p.name for p in organize.collect_files(self.tmp, depth=99)}
        self.assertNotIn("old.jpg", names)

    def test_skips_hidden(self):
        names = {p.name for p in organize.collect_files(self.tmp, depth=0)}
        self.assertNotIn(".hidden.txt", names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
