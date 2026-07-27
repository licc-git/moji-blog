"""Flask CLI 自定义命令。

通过 `flask init-db`、`flask init-admin` 等命令完成项目初始化，
避免手动执行 SQL 或进入 shell。
"""

import click

from app.extensions import db
from app.models import (
    User,
    Category,
    Post,
    DEFAULT_CATEGORIES,
    CATEGORY_STUDY,
    CATEGORY_DAILY,
)


def register_cli_commands(app):
    """将自定义命令注册到 Flask CLI。"""

    @app.cli.command("init-db")
    def init_db():
        """创建所有数据库表。"""
        db.create_all()
        click.secho("✓ 数据库表已创建。", fg="green")

    @app.cli.command("drop-db")
    @click.confirmation_option(prompt="确定要删除所有数据表吗？此操作不可恢复！")
    def drop_db():
        """删除所有数据库表（危险操作）。"""
        db.drop_all()
        click.secho("✓ 所有数据表已删除。", fg="yellow")

    @app.cli.command("init-admin")
    @click.option("--username", default=None, help="管理员用户名（默认读取配置）")
    @click.option("--email", default=None, help="管理员邮箱")
    @click.option("--password", default=None, help="管理员密码")
    def init_admin(username, email, password):
        """创建或重置管理员账户。"""
        cfg = app.config
        username = username or cfg["ADMIN_USERNAME"]
        email = email or cfg["ADMIN_EMAIL"]
        password = password or cfg["ADMIN_PASSWORD"]

        if not password or password == "change-this-password":
            click.secho("✗ 请通过参数或 .env 设置一个真实的管理员密码。", fg="red")
            raise click.Abort()

        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            action = "创建"
        else:
            user.email = email
            user.set_password(password)
            action = "重置"

        db.session.commit()
        click.secho(f"✓ 管理员账户已{action}：{username} <{email}>", fg="green")

    @app.cli.command("init-categories")
    def init_categories():
        """预置默认分类（学习笔记、日常随笔）。"""
        created = []
        for item in DEFAULT_CATEGORIES:
            existing = Category.query.filter_by(name=item["name"]).first()
            if existing:
                continue
            cat = Category(name=item["name"], description=item["description"], sort_order=item.get("sort_order", 0))
            db.session.add(cat)
            created.append(item["name"])
        db.session.commit()
        if created:
            click.secho(f"✓ 已创建分类：{', '.join(created)}", fg="green")
        else:
            click.secho("默认分类已存在，无需创建。", fg="yellow")

    @app.cli.command("seed")
    def seed():
        """一键初始化：建表 + 预置分类 + 创建管理员。"""
        db.create_all()
        click.secho("✓ 数据库表已创建。", fg="green")

        for item in DEFAULT_CATEGORIES:
            if not Category.query.filter_by(name=item["name"]).first():
                db.session.add(Category(name=item["name"], description=item["description"], sort_order=item.get("sort_order", 0)))
        db.session.commit()
        click.secho("✓ 默认分类已就绪。", fg="green")

        cfg = app.config
        password = cfg["ADMIN_PASSWORD"]
        if password and password != "change-this-password":
            user = User.query.filter_by(username=cfg["ADMIN_USERNAME"]).first()
            if user is None:
                user = User(
                    username=cfg["ADMIN_USERNAME"],
                    email=cfg["ADMIN_EMAIL"],
                )
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                click.secho(f"✓ 管理员已创建：{cfg['ADMIN_USERNAME']}", fg="green")
            else:
                click.secho("管理员已存在，跳过创建。", fg="yellow")
        else:
            click.secho(
                "⚠ 未创建管理员：请在 .env 设置 ADMIN_PASSWORD 后运行 `flask init-admin`。",
                fg="yellow",
            )

        # 创建示例文章，方便预览效果
        if Post.query.count() == 0:
            admin = User.query.first()
            study = Category.query.filter_by(name=CATEGORY_STUDY).first()
            daily = Category.query.filter_by(name=CATEGORY_DAILY).first()
            if admin and study:
                _create_sample_post(admin, study)
            if admin and daily:
                _create_sample_post(admin, daily, kind="daily")
            db.session.commit()
            click.secho("✓ 已添加 2 篇示例文章。", fg="green")

        click.secho("\n初始化完成！运行 `uv run flask run` 启动应用。", fg="cyan")


def _create_sample_post(author, category, kind="study"):
    """创建一篇示例文章。"""
    from app.utils.markdown_utils import render_markdown

    if kind == "study":
        title = "Hello, Flask：应用工厂模式入门"
        content = """## 为什么用工厂模式？

Flask 的 **应用工厂模式**（Application Factory Pattern）通过 `create_app()` 函数返回应用实例，带来三大好处：

1. **配置分离**：同一份代码可加载开发、生产、测试等不同配置
2. **多实例支持**：可在同一进程内创建多个应用（如测试）
3. **扩展延迟初始化**：扩展对象全局唯一，绑定时机可控

### 示例

```python
def create_app(config_name=None):
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))
    db.init_app(app)
    return app
```

> 配合 `uv` 管理依赖，开发体验非常顺滑。"""
        tags = "Python, Flask, 教程"
    else:
        title = "周末的咖啡馆：一份闲适的午后记录"
        content = """## 偶然的落脚点

周末午后，雨刚停。沿着老街走了二十分钟，推开一家木门咖啡馆。

空气里混着烘焙的焦香与一点点湿漉漉的木头味。店主在吧台后低头磨豆，没有招呼，只是抬眼笑了笑。

### 一杯手冲

点了一杯耶加雪菲，水温 92℃，粉水比 1:15。

入口是明亮的柑橘酸，尾段带着茉莉花香，干净得像雨后的窗。

### 小结

| 项目 | 评分 |
| --- | --- |
| 环境 | ★★★★☆ |
| 咖啡 | ★★★★★ |
| 价格 | ★★★☆☆ |

有时候，一杯好咖啡和一个安静的下午，就是生活给的奖励。"""
        tags = "生活, 咖啡, 随笔"

    post = Post(
        title=title,
        content_md=content,
        content_html=render_markdown(content),
        category=category,
        author=author,
        tags=tags,
        is_published=True,
    )
    db.session.add(post)
