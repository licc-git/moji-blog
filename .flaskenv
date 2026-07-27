# Flask 开发配置：读取 .flaskenv 与 .env
FLASK_APP=wsgi:app
FLASK_ENV=development
# 绑定所有网卡 + 非 5000 端口（WSL2 下 5000 常被 Windows 侧服务抢占）
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=5099
