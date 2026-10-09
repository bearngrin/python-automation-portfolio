#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
organizer.py - 文件批量整理工具

扫描目标目录,按文件扩展名把文件分类移动到子文件夹中;
可选:文件名加日期前缀、按内容去重。

只用 Python 标准库,无第三方依赖。

用法示例:
    python organizer.py ./demo_messy            # 默认 dry-run,只预览不执行
    python organizer.py ./demo_messy --go       # 真正执行移动
    python organizer.py ./demo_messy --go --rename --dedup --recursive
"""

import argparse
import hashlib
import os
import shutil
import sys
from datetime import datetime

# 扩展名(小写,含点) -> 分类文件夹名
CATEGORIES = {
    "images":   {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"},
    "documents": {".pdf", ".docx", ".doc", ".txt", ".md", ".rtf"},
    "sheets":   {".xlsx", ".xls", ".csv", ".tsv"},
    "archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
    "media":    {".mp4", ".mp3", ".avi", ".mov", ".mkv", ".wav", ".flac"},
}
OTHERS_DIR = "others"
DUPLICATES_DIR = "duplicates"
# 递归扫描时跳过这些整理产物文件夹,避免重复处理
SKIP_DIRS = set(CATEGORIES) | {OTHERS_DIR, DUPLICATES_DIR}


def category_of(filename: str) -> str:
    """根据扩展名返回分类文件夹名,未知扩展名归入 others。"""
    ext = os.path.splitext(filename)[1].lower()
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return cat
    return OTHERS_DIR


def sha256_of(path: str, chunk_size: int = 65536) -> str:
    """计算文件 sha256,用于内容去重。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def unique_dest(directory: str, filename: str) -> str:
    """目标目录已存在同名文件时,自动加序号后缀避免覆盖。

    例如 report.pdf 已存在 -> report_1.pdf -> report_2.pdf ...
    """
    base, ext = os.path.splitext(filename)
    dest = os.path.join(directory, filename)
    n = 1
    while os.path.exists(dest):
        dest = os.path.join(directory, f"{base}_{n}{ext}")
        n += 1
    return dest


def collect_files(target: str, recursive: bool) -> list:
    """收集待整理的文件路径(排序保证行为确定性)。"""
    files = []
    if recursive:
        for root, dirs, filenames in os.walk(target):
            # 跳过整理产物文件夹
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for name in filenames:
                files.append(os.path.join(root, name))
    else:
        for name in os.listdir(target):
            path = os.path.join(target, name)
            if os.path.isfile(path):
                files.append(path)
    return sorted(files)


def plan_moves(target: str, files: list, rename: bool, dedup: bool) -> list:
    """生成移动计划: [(源路径, 目标路径, 原因), ...]。

    原因用于日志说明: categorized(按扩展名分类) / duplicate(内容重复)。
    """
    plans = []
    seen_hashes = {}  # sha256 -> 首次出现的文件路径

    for src in files:
        # --- 去重判定 ---
        if dedup:
            try:
                digest = sha256_of(src)
            except OSError as e:
                print(f"[跳过] 无法读取文件: {src} ({e})")
                continue
            if digest in seen_hashes:
                dst_dir = os.path.join(target, DUPLICATES_DIR)
                plans.append((src, dst_dir, "duplicate"))
                continue
            seen_hashes[digest] = src

        # --- 按扩展名分类 ---
        dst_dir = os.path.join(target, category_of(os.path.basename(src)))
        plans.append((src, dst_dir, "categorized"))

    # --- 应用日期前缀并解决同名冲突 ---
    final = []
    for src, dst_dir, reason in plans:
        name = os.path.basename(src)
        if rename:
            try:
                mtime = os.path.getmtime(src)
            except OSError as e:
                print(f"[跳过] 无法读取修改时间: {src} ({e})")
                continue
            date_prefix = datetime.fromtimestamp(mtime).strftime("%Y%m%d")
            name = f"{date_prefix}_{name}"
        dst = unique_dest(dst_dir, name)
        if dst != os.path.join(dst_dir, name):
            print(f"[提示] 同名文件已存在,自动改名: "
                  f"{name} -> {os.path.basename(dst)}")
        final.append((src, dst, reason))
    return final


def run(target: str, recursive: bool, rename: bool,
        dedup: bool, go: bool) -> int:
    """主流程。返回移动的文件数(出错返回非零在 main 处理)。"""
    target = os.path.abspath(target)
    if not os.path.isdir(target):
        print(f"[错误] 目标目录不存在: {target}", file=sys.stderr)
        return 1

    files = collect_files(target, recursive)
    if not files:
        print(f"[完成] 目录为空或无文件可整理: {target}")
        return 0

    print(f"[扫描] 目标目录: {target}")
    print(f"[扫描] 发现 {len(files)} 个文件"
          f" (recursive={'开' if recursive else '关'}, "
          f"rename={'开' if rename else '关'}, "
          f"dedup={'开' if dedup else '关'})")

    plans = plan_moves(target, files, rename, dedup)
    if not plans:
        print("[完成] 没有需要移动的文件。")
        return 0

    mode = "执行" if go else "预览(dry-run)"
    print(f"[计划] 共 {len(plans)} 个移动操作 [{mode}]:")
    for src, dst, reason in plans:
        rel_src = os.path.relpath(src, target)
        rel_dst = os.path.relpath(dst, target)
        tag = "重复文件" if reason == "duplicate" else "分类整理"
        print(f"  [{tag}] {rel_src}  ->  {rel_dst}")

    if not go:
        print("[提示] 当前为 dry-run 预览模式,未实际移动任何文件。"
              "确认无误后加 --go 真正执行。")
        return 0

    moved, failed = 0, 0
    for src, dst, _ in plans:
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            moved += 1
        except OSError as e:
            failed += 1
            print(f"[失败] {src} -> {dst} ({e})", file=sys.stderr)

    print(f"[完成] 成功移动 {moved} 个文件"
          + (f",失败 {failed} 个" if failed else "") + "。")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="文件批量整理工具:按扩展名分类、加日期前缀、内容去重。"
    )
    parser.add_argument("target", help="要整理的目标目录")
    parser.add_argument("--recursive", action="store_true",
                        help="递归扫描子目录(默认只扫描顶层)")
    parser.add_argument("--rename", action="store_true",
                        help="移动时给文件名加 YYYYMMDD_ 日期前缀(取文件修改时间)")
    parser.add_argument("--dedup", action="store_true",
                        help="用 sha256 找出内容重复的文件,重复的移入 duplicates/ 文件夹")
    parser.add_argument("--go", action="store_true",
                        help="真正执行移动;不加则为 dry-run 预览模式(默认)")
    args = parser.parse_args()
    return run(args.target, args.recursive, args.rename,
               args.dedup, args.go)


if __name__ == "__main__":
    sys.exit(main())
