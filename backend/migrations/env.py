from alembic import context
from sqlalchemy import create_engine, pool

from hospital.core.config import load_settings
from hospital.core.database import Base
import hospital.core.models  # noqa: F401 — registra metadata

settings = load_settings()
target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(
        url=settings.connection_url, target_metadata=target_metadata,
        literal_binds=True, dialect_opts={"paramstyle": "named"}, compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(settings.connection_url, poolclass=pool.NullPool,
                           hide_parameters=True, connect_args={"connect_timeout": 2})
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata,
                              compare_type=True, compare_server_default=True)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
