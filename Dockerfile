# 构建依赖
FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim
# 工作目录
WORKDIR /my_blog
# 先复制安装依赖
COPY pyproject.toml uv.lock ./
# 安装依赖
RUN uv sync --locked --extra prod
# 复制项目代码
COPY . .
# gunicorn 需要写 pid 和日志，目录不能缺
RUN mkdir -p run logs uploads
# 让 .venv 里的命令（gunicorn/flask）直接
ENV PATH="/my_blog/.venv/bin:$PATH"
# 容器内监听端口
EXPOSE 5099

CMD ["gunicorn", "-c", "gunicorn.py", "-b", "0.0.0.0:5099", "wsgi:app"]