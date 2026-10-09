# 网站监控告警工具（monitor.py）

只用 Python 标准库实现的通用监控告警框架：定时抓取页面，按配置规则检查，**只有状态变化时才告警**，避免重复轰炸。

## 功能说明

- **两种检查器**（`config.json` 配置）：
  - `keyword`：抓取 URL（支持 `http(s)://` 和 `file://`），关键词**出现 / 消失**时告警
  - `threshold`：用正则从页面提取数字，**超过 / 低于**阈值时告警
- **两种通知器**：
  - `console`：打印告警内容，用于演示和调试
  - `smtp`：真实 SMTP 发邮件，服务器/账号/密码从环境变量读取
- **状态去重**：`state.json` 记录每个检查项上次的状态，首次运行只建基线不告警
- **健壮性**：抓取/解析失败只记日志不崩溃，继续下一个检查项；程序总是正常退出

## 运行方法

```bash
# 控制台通知（演示 / 调试）
python3 monitor.py --config config.json --notifier console

# 邮件通知（环境变量见下表）
SMTP_HOST=smtp.example.com:587 SMTP_USER=you@example.com SMTP_PASS=xxxx \
    python3 monitor.py --config config.json --notifier smtp

# 清空状态文件，下次按首次运行处理
python3 monitor.py --reset
```

## 配置说明（config.json）

```json
{
  "smtp": {
    "recipients": ["ops@example.com"],
    "subject_prefix": "【监控告警】"
  },
  "checks": [
    {
      "name": "官网促销公告监控",
      "type": "keyword",
      "url": "file://demo/announce.html",
      "keyword": "促销",
      "mode": "appears"
    },
    {
      "name": "金价监控",
      "type": "threshold",
      "url": "https://example.com/gold.html",
      "regex": "金价[：:]\\s*(\\d+)",
      "comparator": "gt",
      "threshold": 1000
    }
  ]
}
```

字段说明：

| 字段 | 说明 |
|---|---|
| `type` | `keyword` 或 `threshold` |
| `url` | 监控地址，支持 `http(s)://` 和 `file://`；`file://` 相对路径按配置文件所在目录解析 |
| `keyword` / `mode` | 关键词检查用；`mode` 为 `appears`（出现告警）或 `disappears`（消失告警） |
| `regex` / `comparator` / `threshold` | 阈值检查用；正则第一个捕获组必须是数字，`comparator` 为 `gt/ge/lt/le` 之一 |
| `recipients` | 可选，单个检查项覆盖全局收件人 |

## SMTP 配置说明

| 环境变量 | 说明 | 示例 |
|---|---|---|
| `SMTP_HOST` | SMTP 服务器，格式 `host` 或 `host:port`（默认 587） | `smtp.qq.com:587` |
| `SMTP_USER` | 登录账号（可空，部分服务器允许匿名发送） | `you@qq.com` |
| `SMTP_PASS` | 密码或授权码 | `xxxx` |

收件人从 `config.json` 的 `smtp.recipients` 读取。发送时自动尝试 STARTTLS，服务器不支持则降级继续。

> 说明：本仓库不附带真实邮件发送演示，因为演示环境没有真实邮箱凭证。
> SMTP 的参数校验逻辑已验证：未设置 `SMTP_HOST` 时程序输出清晰报错并退出（exit 1），不会抛 traceback：
>
> ```
> [2026-10-09 13:13:31] [INFO] 加载配置: config.json,共 1 个检查项
> [2026-10-09 13:13:31] [ERROR] 未设置环境变量 SMTP_HOST (格式: host 或 host:port)
> ```

## 运行演示

场景：监控公司官网公告页（`demo/announce.html`，数据纯属虚构），"促销"关键词一出现就告警。

### 第一次运行：建立基线，不告警

```bash
$ python3 monitor.py --config config.json --notifier console
[2026-10-09 13:13:20] [INFO] 加载配置: config.json,共 1 个检查项
[2026-10-09 13:13:20] [INFO] [官网促销公告监控] 首次运行,建立基线(关键词未出现),不告警
[2026-10-09 13:13:20] [INFO] 状态已保存: /home/hatch/workspace/.jarvis/idea-executions/7fb63153-d7c6-4f45-87e3-9b3e917b0582/scratch/04-notify-monitor/state.json
```

此时 `state.json` 记录 `{"官网促销公告监控": {"present": false}}`。

### 往公告页加一行促销信息后，第二次运行：触发告警

```bash
$ python3 monitor.py --config config.json --notifier console
[2026-10-09 13:13:23] [INFO] 加载配置: config.json,共 1 个检查项

============================================================
[告警] 官网促销公告监控
时间: 2026-10-09 13:13:23
检查项: 官网促销公告监控 (keyword)
URL: file:///home/hatch/workspace/.jarvis/idea-executions/7fb63153-d7c6-4f45-87e3-9b3e917b0582/scratch/04-notify-monitor/demo/announce.html
详情: 关键词"促销"出现在页面中 (之前: 未出现)
============================================================

[2026-10-09 13:13:23] [INFO] 状态已保存: /home/hatch/workspace/.jarvis/idea-executions/7fb63153-d7c6-4f45-87e3-9b3e917b0582/scratch/04-notify-monitor/state.json
```

第三次再跑：状态无变化，不再重复告警（已验证）。

> 以上输出为真实运行结果（演示页已还原，`state.json` 已清理，可按上述步骤完整复现）。

## 错误处理（已验证）

- 抓取失败（如目标站点连不上）：记 `[ERROR]` 日志，跳过该检查项继续下一个，程序正常退出（exit 0）
- 正则未匹配 / 提取到非数字 / 未知检查类型：记 `[ERROR]` 日志并跳过
- 单个检查项抛异常：捕获后继续，不影响其他检查项

## 文件清单

| 文件 | 说明 |
|---|---|
| `monitor.py` | 主程序，仅标准库 |
| `config.json` | 监控配置（演示：1 个 keyword 检查） |
| `demo/announce.html` | 虚构的公司公告页（演示用数据源） |
| `README.md` | 本文档 |
| `.gitignore` | 忽略 `state.json`（运行时状态，不应入库） |
