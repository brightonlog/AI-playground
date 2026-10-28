from logging.config import fileConfig

from alembic import context

from app.db.models import Base
from app.db.session import engine

if context.config.config_file_name:
    fileConfig(context.config.config_file_name)

with engine.connect() as connection:
    # render_as_batch: SQLite cannot ALTER most columns in place.
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
