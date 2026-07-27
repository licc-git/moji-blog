"""Flask 扩展实例集中定义。

将扩展对象放在单独的模块中，而非在 create_app 内部创建，
是为了遵循「应用工厂模式」的最佳实践：
扩展对象全局唯一，但直到 create_app() 调用 init_app 后才与应用绑定，
从而支持多应用、测试隔离与延迟初始化。
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf import CSRFProtect

# 数据库 ORM
db = SQLAlchemy()

# 登录管理
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "请先登录后再进行此操作。"
login_manager.login_message_category = "warning"

# 数据库迁移
migrate = Migrate()

# CSRF 保护
csrf = CSRFProtect()
