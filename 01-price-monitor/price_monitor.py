#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品价格监控 price_monitor.py

读取 config.json 中的商品列表，抓取页面并用正则提取当前价格，
把结果追加记入 prices.csv；与上次记录对比，降价 / 跌破阈值时输出提醒。

只依赖 Python 标准库。
"""

import argparse
import csv
import json
import os
import re
import sys
import urllib.request
from datetime import datetime

CSV_HEADER = ["时间", "商品", "价格"]
FETCH_TIMEOUT = 15


def parse_price(raw: str) -> float:
    """把 '¥1,599.00' / '329' 这类字符串转成 float。"""
    cleaned = raw.replace(",", "").strip()
    cleaned = re.sub(r"^[^\d.]+", "", cleaned)   # 去掉开头的货币符号等
    cleaned = re.sub(r"[^\d.]+$", "", cleaned)   # 去掉结尾的单位等
    return float(cleaned)


def fetch_html(url: str) -> str:
    """抓取页面 HTML，自动按 charset 解码；失败时抛异常给上层处理。"""
    req = urllib.request.Request(url, headers={"User-Agent": "price-monitor/1.0"})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
        data = resp.read()
    # 优先用响应头里的 charset，否则按 utf-8 / gbk 依次尝试
    charset = resp.headers.get_content_charset() if hasattr(resp, "headers") else None
    for enc in [c for c in (charset, "utf-8", "gbk") if c]:
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def load_last_prices(csv_path: str) -> dict:
    """读 prices.csv，返回 {商品名: 上次价格}。文件不存在时返回空字典。"""
    last = {}
    if not os.path.exists(csv_path):
        return last
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                try:
                    last[row["商品"]] = float(row["价格"])
                except (KeyError, ValueError):
                    continue
    except OSError as e:
        print(f"[警告] 读取历史记录失败({csv_path}): {e}", file=sys.stderr)
    return last


def append_record(csv_path: str, name: str, price: float) -> None:
    """把本次结果追加到 prices.csv（不存在则先写表头）。"""
    need_header = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if need_header:
            writer.writerow(CSV_HEADER)
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name, f"{price:.2f}"])


def check_one(target: dict, last_prices: dict, csv_path: str) -> bool:
    """检查单个商品，返回 True 表示成功，False 表示失败。"""
    name = target.get("name", "<未命名>")
    url = target.get("url", "")
    pattern = target.get("pattern", "")
    threshold = target.get("threshold")

    # --- 抓取 ---
    try:
        html = fetch_html(url)
    except Exception as e:
        print(f"[失败] {name}: 页面抓取失败（{type(e).__name__}: {e}），已跳过")
        return False

    # --- 提取价格 ---
    try:
        m = re.search(pattern, html)
    except re.error as e:
        print(f"[失败] {name}: 正则表达式无效（{e}），已跳过")
        return False
    if not m:
        print(f"[失败] {name}: 页面中未匹配到价格（pattern 未命中），已跳过")
        return False
    try:
        price = parse_price(m.group(1))
    except ValueError:
        print(f"[失败] {name}: 提取到 {m.group(1)!r} 但无法解析为数字，已跳过")
        return False

    # --- 记录 ---
    append_record(csv_path, name, price)

    # --- 对比 ---
    old = last_prices.get(name)
    tag = "[持平]"
    detail = f"当前 ¥{price:.2f}"
    if old is None:
        tag, detail = "[基线]", f"首次记录 ¥{price:.2f}"
    elif price < old:
        tag = "[降价]"
        detail = f"¥{old:.2f} → ¥{price:.2f}（降了 ¥{old - price:.2f}）"
    elif price > old:
        tag = "[涨价]"
        detail = f"¥{old:.2f} → ¥{price:.2f}（涨了 ¥{price - old:.2f}）"
    print(f"{tag} {name}: {detail}")

    # --- 阈值告警 ---
    if threshold is not None and price < threshold:
        print(f"  ※※※ 告警：已跌破阈值 ¥{threshold:.2f}，当前 ¥{price:.2f} ※※※")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="商品价格监控：抓取页面价格并记录对比")
    parser.add_argument("--config", default="config.json", help="配置文件路径（默认 config.json）")
    args = parser.parse_args()

    # 配置文件与工作目录：csv 落在配置文件同目录
    if not os.path.exists(args.config):
        print(f"[错误] 找不到配置文件: {args.config}", file=sys.stderr)
        return 2
    base_dir = os.path.dirname(os.path.abspath(args.config))
    csv_path = os.path.join(base_dir, "prices.csv")

    try:
        with open(args.config, encoding="utf-8") as f:
            config = json.load(f)
        targets = config["targets"]
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[错误] 配置文件解析失败: {e}", file=sys.stderr)
        return 2

    print(f"开始检查 {len(targets)} 个商品（{datetime.now():%Y-%m-%d %H:%M}）")
    print("-" * 50)

    last_prices = load_last_prices(csv_path)
    ok = sum(check_one(t, last_prices, csv_path) for t in targets)

    print("-" * 50)
    print(f"完成：成功 {ok}/{len(targets)}，记录已写入 {csv_path}")
    return 0 if ok == len(targets) else 1


if __name__ == "__main__":
    sys.exit(main())
