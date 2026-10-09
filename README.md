# Python 自动化作品集

4 个独立、可直接运行的 Python 自动化小作品，每个都带中文 README 和真实运行演示。定位是接单作品集：展示真实工程习惯（参数化输入、错误处理、清晰输出），不写玩具脚本。

演示数据全部虚构，不含任何真实隐私数据。

## 作品列表

| 目录 | 作品 | 一句话介绍 |
|------|------|-----------|
| [01-price-monitor](01-price-monitor/) | 网页价格监控 | 配置驱动的商品价格抓取与降价告警，价格历史存 CSV |
| [02-excel-report](02-excel-report/) | Excel 销售报表自动化 | 合并多月销售明细，一键生成带汇总表的格式化报告 |
| [03-file-organizer](03-file-organizer/) | 文件批量整理 | 按类型分类、日期重命名、SHA256 去重，默认 dry-run 预览 |
| [04-notify-monitor](04-notify-monitor/) | 监控告警通知 | 网页关键词 / 数值阈值监控，状态去重防轰炸，支持邮件发送 |

## 快速开始

每个作品目录下都有中文 README，含完整运行方法。通用流程：

```bash
cd 01-price-monitor
python3 price_monitor.py --help
```

- `01-price-monitor`：只用 Python 标准库，零依赖
- `02-excel-report`：需要 `pip install openpyxl`
- `03-file-organizer`：只用 Python 标准库，零依赖
- `04-notify-monitor`：只用 Python 标准库，零依赖（邮件发送需自行配置 SMTP 环境变量）

## 运行环境

Python 3.12，macOS / Linux / Windows 均可。
