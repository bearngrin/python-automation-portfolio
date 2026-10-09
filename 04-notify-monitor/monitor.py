#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
monitor.py -- 通用监控告警工具(仅 Python 标准库)

功能:
  1. keyword 检查  : 抓取 URL(支持 http(s):// 与 file://),监控关键词出现/消失
  2. threshold 检查: 用正则从页面提取数字,超过/低于阈值时告警
  3. 通知方式      : console(打印,用于演示调试) / smtp(真实邮件发送)
  4. 状态去重      : state.json 记录每个检查项上次状态,仅状态变化时告警

用法:
  python3 monitor.py --config config.json --notifier console
  python3 monitor.py --config config.json --notifier smtp
  python3 monitor.py --reset            # 清空状态,下次按首次运行处理
"""

import argparse
import json
import os
import re
import smtplib
import sys
import urllib.request
from datetime import datetime
from email.message import EmailMessage
from urllib.parse import unquote


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(level, msg):
    print("[%s] [%s] %s" % (now_str(), level, msg), flush=True)


def fetch_text(url, timeout=15):
    """抓取 URL 文本。支持 http(s):// 与 file://,失败返回 None。"""
    try:
        if url.startswith("file://"):
            path = unquote(url[len("file://"):])
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (compatible; monitor.py/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except Exception as e:
        # 抓取失败只记录,不中断整体流程
        log("ERROR", "抓取失败 %s: %s" % (url, e))
        return None


def resolve_url(url, base_dir):
    """file:// 相对路径按配置文件所在目录解析,保证演示可移植。"""
    if url.startswith("file://"):
        p = unquote(url[len("file://"):])
        if not os.path.isabs(p):
            p = os.path.normpath(os.path.join(base_dir, p))
            return "file://" + p
    return url


def run_keyword(check, old):
    """关键词检查。mode=appears: False->True 告警; mode=disappears: True->False 告警。"""
    text = fetch_text(check["url"])
    if text is None:
        return None, None  # 抓取失败:状态不变,不告警
    present = check["keyword"] in text
    mode = check.get("mode", "appears")
    new_state = {"present": present}
    alert = None
    if old is None:
        log("INFO", "[%s] 首次运行,建立基线(关键词%s),不告警"
            % (check["name"], "出现" if present else "未出现"))
    else:
        was = old.get("present", False)
        if mode == "appears" and present and not was:
            alert = "关键词\"%s\"出现在页面中 (之前: 未出现)" % check["keyword"]
        elif mode == "disappears" and not present and was:
            alert = "关键词\"%s\"从页面中消失 (之前: 出现)" % check["keyword"]
    return new_state, alert


def run_threshold(check, old):
    """阈值检查。用正则提取第一个捕获组的数字,与阈值比较;仅 ok->超限 告警。"""
    text = fetch_text(check["url"])
    if text is None:
        return None, None
    m = re.search(check["regex"], text)
    if not m:
        log("ERROR", "[%s] 正则未匹配到数字: %s" % (check["name"], check["regex"]))
        return None, None
    try:
        value = float(m.group(1).replace(",", ""))
    except ValueError:
        log("ERROR", "[%s] 提取到的不是有效数字: %r" % (check["name"], m.group(1)))
        return None, None
    comp = check.get("comparator", "gt")
    th = float(check["threshold"])
    ops = {"gt": ">", "ge": ">=", "lt": "<", "le": "<="}
    if comp not in ops:
        log("ERROR", "[%s] 未知的 comparator: %s,应为 gt/ge/lt/le 之一"
            % (check["name"], comp))
        return None, None
    violated = {"gt": value > th, "ge": value >= th,
                "lt": value < th, "le": value <= th}[comp]
    new_state = {"value": value, "violated": violated}
    alert = None
    op = ops[comp]
    if old is None:
        log("INFO", "[%s] 首次运行,建立基线(当前值 %s,阈值 %s %s),不告警"
            % (check["name"], value, op, th))
    elif violated and not old.get("violated", False):
        alert = "数值 %s %s 阈值 %s,触发告警 (之前: 未超限)" % (value, op, th)
    elif not violated and old.get("violated", False):
        log("INFO", "[%s] 数值恢复正常: %s (阈值 %s %s)"
            % (check["name"], value, op, th))
    return new_state, alert


class ConsoleNotifier:
    """控制台通知:打印告警内容,用于演示和调试。"""

    def send(self, title, body):
        line = "=" * 60
        print("\n%s\n[告警] %s\n时间: %s\n%s\n%s\n"
              % (line, title, now_str(), body, line), flush=True)


class SMTPNotifier:
    """SMTP 邮件通知。服务器/账号/密码从环境变量读取,收件人从配置读取。"""

    def __init__(self, recipients, subject_prefix="【监控告警】"):
        host_port = os.environ.get("SMTP_HOST", "")
        if not host_port:
            raise ValueError("未设置环境变量 SMTP_HOST (格式: host 或 host:port)")
        self.user = os.environ.get("SMTP_USER", "")
        self.password = os.environ.get("SMTP_PASS", "")
        if ":" in host_port:
            self.host, port = host_port.rsplit(":", 1)
            self.port = int(port)
        else:
            self.host, self.port = host_port, 587
        if not recipients:
            raise ValueError("收件人列表为空,请在 config.json 的 smtp.recipients 中配置")
        self.recipients = recipients
        self.subject_prefix = subject_prefix

    def send(self, title, body):
        msg = EmailMessage()
        msg["Subject"] = "%s%s" % (self.subject_prefix, title)
        msg["From"] = self.user or "monitor@localhost"
        msg["To"] = ", ".join(self.recipients)
        msg.set_content("%s\n时间: %s\n\n%s" % (title, now_str(), body))
        with smtplib.SMTP(self.host, self.port, timeout=20) as s:
            try:
                s.starttls()
            except Exception as e:
                log("WARN", "STARTTLS 不可用,继续尝试发送: %s" % e)
            if self.user:
                s.login(self.user, self.password)
            s.send_message(msg)
        log("INFO", "邮件已发送至 %s" % ", ".join(self.recipients))


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except Exception as e:
        log("ERROR", "读取 %s 失败: %s" % (path, e))
        return default


def main(argv=None):
    ap = argparse.ArgumentParser(description="通用监控告警工具(仅标准库)")
    ap.add_argument("--config", default="config.json", help="配置文件路径")
    ap.add_argument("--notifier", choices=["console", "smtp"], default="console",
                    help="通知方式")
    ap.add_argument("--reset", action="store_true", help="清空状态文件后退出")
    args = ap.parse_args(argv)

    cfg_path = args.config
    cfg_dir = os.path.dirname(os.path.abspath(cfg_path))
    state_path = os.path.join(cfg_dir, "state.json")

    if args.reset:
        if os.path.exists(state_path):
            os.remove(state_path)
            log("INFO", "已清空状态文件: %s" % state_path)
        else:
            log("INFO", "状态文件不存在,无需清空")
        return 0

    config = load_json(cfg_path, None)
    if not config or not isinstance(config.get("checks"), list):
        log("ERROR", "配置文件无效: %s" % cfg_path)
        return 1
    checks = config["checks"]
    log("INFO", "加载配置: %s,共 %d 个检查项" % (cfg_path, len(checks)))

    state = load_json(state_path, {})
    if not isinstance(state, dict):
        state = {}

    if args.notifier == "smtp":
        smtp_cfg = config.get("smtp", {})
        try:
            notifier = SMTPNotifier(
                smtp_cfg.get("recipients", []),
                smtp_cfg.get("subject_prefix", "【监控告警】"))
        except ValueError as e:
            log("ERROR", str(e))
            return 1
    else:
        notifier = ConsoleNotifier()

    for check in checks:
        name = check.get("name", "?")
        ctype = check.get("type")
        try:
            check["url"] = resolve_url(check.get("url", ""), cfg_dir)
            if ctype == "keyword":
                new_state, alert = run_keyword(check, state.get(name))
            elif ctype == "threshold":
                new_state, alert = run_threshold(check, state.get(name))
            else:
                log("ERROR", "[%s] 未知的检查类型: %s,跳过" % (name, ctype))
                continue
        except Exception as e:
            # 单个检查项异常不影响其他项
            log("ERROR", "[%s] 检查异常: %s" % (name, e))
            continue
        if new_state is not None:
            state[name] = new_state
        if alert:
            body = ("检查项: %s (%s)\nURL: %s\n详情: %s"
                    % (name, ctype, check["url"], alert))
            try:
                recips = check.get("recipients")
                if args.notifier == "smtp" and recips:
                    SMTPNotifier(recips).send(name, body)
                else:
                    notifier.send(name, body)
            except Exception as e:
                log("ERROR", "[%s] 通知发送失败: %s" % (name, e))

    try:
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        log("INFO", "状态已保存: %s" % state_path)
    except Exception as e:
        log("ERROR", "保存状态失败: %s" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
