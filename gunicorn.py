"""Gunicorn 配置文件（Unix Socket 模式，生产环境推荐）。

启动方式：
    uv run --extra prod gunicorn -c gunicorn.py wsgi:app

停止：
    kill $(cat run/gunicorn.pid)

平滑重载（不中断服务）：
    kill -HUP $(cat run/gunicorn.pid)
"""

import os
# import multiprocessing
from pathlib import Path

# 项目根目录（字符串类型，避免 pathlib 与 gunicorn 的类型不兼容问题）
BASE_DIR = Path(__file__).resolve().parent

# ─── 网络绑定 ───
# 使用 Unix Socket 比 TCP 端口性能更好，适合 Nginx + Gunicorn 本地通信
bind = f"unix:{BASE_DIR}/run/moji_blog.sock"
# 备用：TCP 端口模式（调试时用）
# bind = "127.0.0.1:8000"

# 监听队列长度（积压请求数）
backlog = 512

# ─── 进程配置 ───
# 工作进程数：CPU 核数 × 2 + 1 是经验公式
# workers = multiprocessing.cpu_count() * 2 + 1
workers = 4
# 工作模式：gevent 支持异步，适合 I/O 密集型（博客类推荐）
worker_class = "gevent"
# 每个 worker 的最大并发连接数（gevent 模式下生效）
worker_connections = 1000

# 工作目录
chdir = str(BASE_DIR)

# 超时时间（秒），超时后 worker 会被重启
timeout = 30
# 优雅关闭超时（秒）
graceful_timeout = 30
# keep-alive 超时（秒）
keepalive = 5

# 防内存泄漏：每个 worker 处理多少请求后自动重启
max_requests = 1000
# 随机抖动，避免所有 worker 同时重启
max_requests_jitter = 100

# ─── 进程文件 ───
# PID 文件路径，用于管理进程启停
pidfile = str(BASE_DIR / "run" / "gunicorn.pid")

# ─── 日志配置 ───
# 日志级别：debug / info / warning / error / critical
loglevel = "info"
# 捕获标准输出/错误到日志文件
capture_output = True
# 访问日志文件
accesslog = str(BASE_DIR / "logs" / "gunicorn_access.log")
# 错误日志文件
errorlog = str(BASE_DIR / "logs" / "gunicorn_error.log")


# 访问日志格式
access_log_format = (
    '%(t)s %(p)s %(h)s "%(r)s" %(s)s %(L)s %(b)s %(f)s" "%(a)s"'
)

# ─── 安全 ───
# 限制请求头大小（防止攻击）
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
