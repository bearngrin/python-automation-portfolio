# Excel 销售报表自动化

把每个月导出的销售明细 xlsx 一键合并，自动生成带三个汇总表的《销售汇总报告.xlsx》。
适合连锁门店、电商小团队每月/每周出报表的场景：明细丢进目录，运行一条命令，报告就出来了。

## 功能说明

| 脚本 | 作用 |
|---|---|
| `gen_sample.py` | 一键生成演示数据：在 `data/` 下生成 3 个月份的销售明细（`2026-01.xlsx` ~ `2026-03.xlsx`），列为 日期,门店,商品,数量,单价,金额。数据全部虚构，随机种子固定（默认 42），每次运行结果一致 |
| `sales_report.py` | 读取数据目录下所有 xlsx 明细并合并，生成汇总报告，包含三个 sheet |

汇总报告的三个 sheet：

- **总览**：总销售额、订单总数、客单价、覆盖月份（另附覆盖门店数、在售商品数）
- **按商品汇总**：各商品销售数量与销售额，按销售额降序
- **按门店汇总**：各门店订单数与销售额，按销售额降序

报告样式：表头加粗、列宽按内容自适应、金额列保留两位小数。

错误处理：数据目录不存在、目录下没有 xlsx、某个文件损坏或表头不符时，都会给出明确提示（损坏/表头不符的文件会被跳过并继续处理其余文件），不会直接崩溃。

## 依赖

```bash
pip install openpyxl
```

仅依赖 openpyxl，无其他第三方包。Python 3.12 实测通过。

## 运行方法

```bash
# 1. 生成演示数据（输出到 ./data/）
python gen_sample.py

# 2. 生成汇总报告（读取 ./data/，输出 ./销售汇总报告.xlsx）
python sales_report.py

# 自定义参数
python gen_sample.py --output-dir ./data --seed 42
python sales_report.py --input ./data --output 销售汇总报告.xlsx
```

| 参数 | 说明 | 默认值 |
|---|---|---|
| `gen_sample.py --output-dir` | 演示数据输出目录 | `data` |
| `gen_sample.py --seed` | 随机种子，固定则结果可复现 | `42` |
| `sales_report.py --input` | 销售明细所在目录 | `data` |
| `sales_report.py --output` | 汇总报告输出文件名 | `销售汇总报告.xlsx` |

## 输入输出示例

**输入**（`data/2026-01.xlsx` 片段，`gen_sample.py` 生成）：

| 日期 | 门店 | 商品 | 数量 | 单价 | 金额 |
|---|---|---|---|---|---|
| 2026-01-03 | 北京朝阳店 | 摩卡 | 4 | 31.52 | 126.08 |
| 2026-01-05 | 上海静安店 | 拿铁 | 2 | 27.31 | 54.62 |

**输出**（`销售汇总报告.xlsx`，三个 sheet）：

总览：

| 指标 | 数值 |
|---|---|
| 总销售额（元） | 14119.70 |
| 订单总数 | 167 |
| 客单价（元） | 84.55 |
| 覆盖月份 | 2026-01、2026-02、2026-03 |

按商品汇总（前 3）：摩卡 2192.63 元 ＞ 卡布奇诺 2040.89 元 ＞ 焦糖玛奇朵 1894.69 元
按门店汇总（前 3）：北京朝阳店 3744.93 元 ＞ 广州天河店 3005.34 元 ＞ 上海徐汇店 2731.86 元

## 运行演示

以下为本机（Python 3.12.3，openpyxl 3.1.2）真实运行输出，汇总数字与报告文件一致：

```
$ python gen_sample.py
[OK] 2026-01.xlsx: 60 行
[OK] 2026-02.xlsx: 50 行
[OK] 2026-03.xlsx: 57 行
共生成 3 个文件，167 行明细 -> data/

$ python sales_report.py
[OK] 2026-01.xlsx: 60 行
[OK] 2026-02.xlsx: 50 行
[OK] 2026-03.xlsx: 57 行
合并 3 个文件，共 167 行明细
报告已生成：销售汇总报告.xlsx（总览 / 按商品汇总 / 按门店汇总）
```

错误处理演示：

```
$ python sales_report.py --input no_such_dir
[ERROR] 数据目录不存在：no_such_dir/

$ python sales_report.py --input /tmp/empty_test
[ERROR] 目录 /tmp/empty_test/ 下没有找到 xlsx 文件
```

## 目录结构

```
02-excel-report/
├── gen_sample.py        # 演示数据生成器
├── sales_report.py      # 汇总报告生成器
├── README.md            # 本说明
├── data/                # 销售明细（gen_sample.py 生成）
│   ├── 2026-01.xlsx
│   ├── 2026-02.xlsx
│   └── 2026-03.xlsx
└── 销售汇总报告.xlsx     # sales_report.py 生成
```
