-- ============================================================
-- 墨记博客 · MySQL 数据库初始化脚本
--
-- 使用方法（需要 MySQL root 或具备 CREATE 权限的账户）：
--   mysql -u root -p < db_init.sql
--
-- 或在 MySQL 容器中：
--   docker exec -i <mysql容器> mysql -uroot -p < db_init.sql
-- ============================================================

-- 1. 创建数据库（utf8mb4 以支持完整 Unicode 与 emoji）
CREATE DATABASE IF NOT EXISTS my_blog
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 2. 创建专用用户（密码需满足 MySQL 密码策略：≥8 位且含大小写字母/数字/特殊字符；
--    若自行修改，需同步更新 .env 中 DATABASE_URL 的密码）
CREATE USER IF NOT EXISTS 'bloguser'@'localhost' IDENTIFIED BY 'Blog!Pass2026';
CREATE USER IF NOT EXISTS 'bloguser'@'%'         IDENTIFIED BY 'Blog!Pass2026';

-- 3. 授权
GRANT ALL PRIVILEGES ON my_blog.* TO 'bloguser'@'localhost';
GRANT ALL PRIVILEGES ON my_blog.* TO 'bloguser'@'%';
FLUSH PRIVILEGES;

-- 完成。接下来在项目目录执行：
--   cp .env.example .env   # 按需修改密码
--   uv run flask seed      # 建表 + 预置分类 + 创建管理员 + 示例文章
