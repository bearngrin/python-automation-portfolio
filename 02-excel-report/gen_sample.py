#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成演示用销售明细数据。

在指定目录下生成 3 个月份的销售明细 xlsx 文件（2026-01.xlsx ~ 2026-03.xlsx），
每表列为：日期,门店,商品,数量,单价,金额。
数据全部虚构，随机种子固定，保证每次运行结果一致（可复现）。

用法:
    python gen_sample.py                 # 生成到 ./data/
    python gen_sample.py --output-dir ./data --seed 42
"""

import argparse
import random
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

# ---------------- 虚构基础数据 ----------------
STORES = ["上海静安店", "上海徐汇店", "北京朝阳店", "杭州西湖店", "广州天河店"]

# 商品: 单价（元）
PRODUCTS = {
    "拿铁": 28.0,
    "美式": 22.0,
    "卡布奇诺": 30.0,
    "摩卡": 32.0,
    "抹茶拿铁": 30.0,
    "焦糖玛奇朵": 33.0,
    "冰滴咖啡": 36.0,
    "柠檬茶": 18.0,
}

MONTHS = [(2026, 1), (2026, 2), (2026, 3)]
HEADERS = ["日期", "门店", "商品", "数量", "单价", "金额"]


def gen_month_rows(year: int, month: int, rng: random.Random) -> list:
    """生成某个月的销售明细行（40~60 行）。"""
    n_rows = rng.randint(40, 60)
    rows = []
    product_names = list(PRODUCTS.keys())
    for _ in range(n_rows):
        day = rng.randint(1, 28)  # 取 1~28 号，避开各月天数差异
        store = rng.choice(STORES)
        product = rng.choice(product_names)
        qty = rng.randint(1, 5)
        # 单价在基准价上下浮动 ±2 元，模拟促销/调价
        price = round(PRODUCTS[product] + rng.uniform(-2, 2), 2)
        amount = round(qty * price, 2)
        rows.append([date(year, month, day).isoformat(), store, product, qty, price, amount])
    # 按日期排序，看起来更像真实导出的明细
    rows.sort(key=lambda r: r[0])
    return rows


def write_xlsx(path: Path, rows: list) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "销售明细"
    ws.append(HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")
    for row in rows:
        ws.append(row)
    # 列宽
    widths = [12, 14, 12, 8, 10, 12]
    for col, w in zip("ABCDEF", widths):
        ws.column_dimensions[col].width = w
    wb.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="生成演示用销售明细 xlsx 数据")
    parser.add_argument("--output-dir", default="data", help="输出目录（默认 data/）")
    parser.add_argument("--seed", type=int, default=42, help="随机种子（默认 42，保证可复现）")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    total = 0
    for year, month in MONTHS:
        rows = gen_month_rows(year, month, rng)
        fname = f"{year}-{month:02d}.xlsx"
        write_xlsx(out_dir / fname, rows)
        total += len(rows)
        print(f"[OK] {fname}: {len(rows)} 行")

    print(f"共生成 {len(MONTHS)} 个文件，{total} 行明细 -> {out_dir}/")


if __name__ == "__main__":
    main()
