# 文件批量整理工具 organizer.py

把乱糟糟的文件夹一键整理好：按文件类型自动分类进子文件夹，可选加日期前缀、按内容去重。
只用 Python 标准库，无第三方依赖，Python 3.8+ 可跑（已在 Python 3.12 验证）。

## 功能说明

| 功能 | 说明 |
|---|---|
| 按扩展名分类 | 图片 / 文档 / 表格 / 压缩包 / 音频视频 / 其他，自动移动到对应子文件夹 |
| `--rename` | 移动时给文件名加 `YYYYMMDD_` 日期前缀（取文件修改时间） |
| `--dedup` | 用 sha256 按内容找重复文件，重复的移入 `duplicates/`（保留第一份） |
| `--recursive` | 递归扫描子目录（默认只扫顶层） |
| dry-run 安全开关 | 默认只预览不执行，加 `--go` 才真正移动 |
| 防覆盖 | 目标已存在同名文件时自动加 `_1`、`_2` 序号后缀 |

分类规则：

| 文件夹 | 扩展名 |
|---|---|
| `images/` | jpg jpeg png gif webp bmp svg |
| `documents/` | pdf docx doc txt md rtf |
| `sheets/` | xlsx xls csv tsv |
| `archives/` | zip rar 7z tar gz |
| `media/` | mp4 mp3 avi mov mkv wav flac |
| `others/` | 其他所有扩展名 / 无扩展名 |

## 运行方法

```bash
# 1. 先预览（默认 dry-run，不动任何文件）
python organizer.py ./demo_messy --rename --dedup

# 2. 确认无误后真正执行
python organizer.py ./demo_messy --rename --dedup --go

# 3. 递归子目录
python organizer.py ./downloads --recursive --go

# 4. 查看全部参数
python organizer.py --help
```

## 运行演示

演示目录 `demo_messy/` 内预置了 15 个测试文件（内容均为虚构），
其中 `copy_a.txt` 与 `copy_b.txt` 内容完全相同，用于演示去重；
`images/` 下预置了一个同名文件，用于演示防覆盖改名。

整理前（`find demo_messy -type f`）：

```
demo_messy/avatar.gif
demo_messy/backup.zip
demo_messy/copy_a.txt
demo_messy/copy_b.txt
demo_messy/data.json
demo_messy/demo.mp4
demo_messy/images/20240305_photo1.jpg
demo_messy/notes.txt
demo_messy/photo1.jpg
demo_messy/readme.md
demo_messy/report.pdf
demo_messy/run.sh
demo_messy/sales.xlsx
demo_messy/screenshot.png
demo_messy/song.mp3
demo_messy/users.csv
```

dry-run 预览输出（`python organizer.py demo_messy --rename --dedup`）：

```
[扫描] 目标目录: /home/hatch/workspace/.../03-file-organizer/demo_messy
[扫描] 发现 15 个文件 (recursive=关, rename=开, dedup=开)
[提示] 同名文件已存在,自动改名: 20240305_photo1.jpg -> 20240305_photo1_1.jpg
[计划] 共 15 个移动操作 [预览(dry-run)]:
  [分类整理] avatar.gif  ->  images/20261009_avatar.gif
  [分类整理] backup.zip  ->  archives/20261009_backup.zip
  [分类整理] copy_a.txt  ->  documents/20260115_copy_a.txt
  [重复文件] copy_b.txt  ->  duplicates/20260115_copy_b.txt
  [分类整理] data.json  ->  others/20261009_data.json
  [分类整理] demo.mp4  ->  media/20251120_demo.mp4
  [分类整理] notes.txt  ->  documents/20261009_notes.txt
  [分类整理] photo1.jpg  ->  images/20240305_photo1_1.jpg
  [分类整理] readme.md  ->  documents/20261009_readme.md
  [分类整理] report.pdf  ->  documents/20240305_report.pdf
  [分类整理] run.sh  ->  others/20261009_run.sh
  [分类整理] sales.xlsx  ->  sheets/20251120_sales.xlsx
  [分类整理] screenshot.png  ->  images/20251120_screenshot.png
  [分类整理] song.mp3  ->  media/20261009_song.mp3
  [分类整理] users.csv  ->  sheets/20261009_users.csv
[提示] 当前为 dry-run 预览模式,未实际移动任何文件。确认无误后加 --go 真正执行。
```

加上 `--go` 真实执行后（`find demo_messy -type f`）：

```
demo_messy/archives/20261009_backup.zip
demo_messy/documents/20240305_report.pdf
demo_messy/documents/20260115_copy_a.txt
demo_messy/documents/20261009_notes.txt
demo_messy/documents/20261009_readme.md
demo_messy/duplicates/20260115_copy_b.txt
demo_messy/images/20240305_photo1.jpg
demo_messy/images/20240305_photo1_1.jpg
demo_messy/images/20251120_screenshot.png
demo_messy/images/20261009_avatar.gif
demo_messy/media/20251120_demo.mp4
demo_messy/media/20261009_song.mp3
demo_messy/others/20261009_data.json
demo_messy/others/20261009_run.sh
demo_messy/sheets/20251120_sales.xlsx
demo_messy/sheets/20261009_users.csv
```

可以看到：
- 15 个文件全部按扩展名归类，日期前缀取自各自的修改时间；
- `copy_b.txt` 因内容与 `copy_a.txt` 完全相同被移入 `duplicates/`；
- `photo1.jpg` 与预置的 `images/20240305_photo1.jpg` 撞名，自动改名为 `20240305_photo1_1.jpg`，原文件未被覆盖。

## 设计说明

- **先规划后执行**：所有移动操作先生成完整计划并打印，dry-run 下直接退出，`--go` 才落盘，避免误操作。
- **确定性行为**：文件按路径排序处理，去重时"保留第一份"的结果可复现。
- **错误隔离**：单个文件读取/移动失败只记一条 `[失败]` 日志，不中断其余文件；最后汇总成功/失败数并返回对应退出码。
- **递归安全**：`--recursive` 会跳过 `images/`、`documents/` 等整理产物文件夹，不会把刚分好的文件再扫一遍。
