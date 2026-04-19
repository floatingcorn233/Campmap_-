import logging
from logging.config import fileConfig

from flask import current_app
from alembic import context

# Alembic 的設定物件（會讀取 alembic.ini 等設定）
config = context.config

# 依照 Alembic 設定初始化日誌
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def get_engine():
    """
    取得目前 Flask 專案綁定的資料庫引擎（engine）
    相容不同版本的 Flask-SQLAlchemy
    """
    try:
        # 舊版 Flask-SQLAlchemy 的寫法
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        # 新版 Flask-SQLAlchemy 的寫法
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    """
    取得資料庫連線 URL，並轉成 Alembic 可用的字串格式
    """
    try:
        return get_engine().url.render_as_string(hide_password=False).replace('%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


# 把目前 Flask 專案的資料庫 URL 寫入 Alembic 設定
config.set_main_option('sqlalchemy.url', get_engine_url())

# 取得 Flask-Migrate 綁定的 db 物件（也就是專案裡的 SQLAlchemy 實例）
target_db = current_app.extensions['migrate'].db


def get_metadata():
    """
    取得模型的 metadata（所有資料表結構資訊）
    Alembic 自動比對資料庫結構時會用到
    """
    if hasattr(target_db, 'metadatas'):
        # Flask-SQLAlchemy 新版本可能使用 metadatas
        return target_db.metadatas[None]
    return target_db.metadata


def run_migrations_offline():
    """
    離線模式執行 migration
    不會真正連接資料庫，只根據 URL 和模型結構產生 SQL
    一般比較少用
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=get_metadata(),
        literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """
    線上模式執行 migration
    會真正連接資料庫並執行遷移
    這是最常見的模式（flask db migrate / upgrade 通常走這裡）
    """

    # 如果 autogenerate 時沒有偵測到結構變化，就不要產生空的 migration 檔案
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    # 讀取 Flask-Migrate 的額外設定參數
    conf_args = current_app.extensions['migrate'].configure_args

    # 如果沒有自訂 process_revision_directives，就使用上面的預設邏輯
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    # 取得資料庫引擎
    connectable = get_engine()

    # 建立資料庫連線，交給 Alembic 執行 migration
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args
        )

        with context.begin_transaction():
            context.run_migrations()


# 根據目前模式決定執行離線或線上 migration
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()