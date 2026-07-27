"""WSGI 入口。

生产环境用 gunicorn 等服务器加载：
    gunicorn "wsgi:app"

开发环境用：
    uv run flask run
"""

from app import create_app

app = create_app()


if __name__ == "__main__":
    # 仅作开发便捷入口；正式开发请使用 `flask run`
    app.run(host="0.0.0.0", port=5099)
