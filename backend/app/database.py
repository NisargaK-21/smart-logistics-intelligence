from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.core.config import settings


class Base(DeclarativeBase):
    pass


engine_options = {"pool_pre_ping": True}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


ALEMBIC_CONFIG_PATH = Path(__file__).resolve().parents[1] / "alembic.ini"


def upgrade_database(target_engine: Engine = engine) -> None:
    try:
        from alembic import command
        from alembic.config import Config

        config = Config(str(ALEMBIC_CONFIG_PATH))
        config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))
        with target_engine.connect() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
    except Exception:
        # Fallback to direct SQLAlchemy metadata creation when Alembic is not installed/configured
        import backend.app.models  # noqa: F401 - ensure models are registered
        Base.metadata.create_all(bind=target_engine)

