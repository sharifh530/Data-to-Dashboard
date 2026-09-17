from alembic import context
from dtd_api.database import make_engine
from dtd_api.models import Base
from dtd_api.settings import Settings

config = context.config


def run(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


supplied = config.attributes.get("connection")
if supplied is not None:
    run(supplied)
else:
    settings = Settings()
    if settings.database_url is None:
        raise RuntimeError("DTD_DATABASE_URL is required; see docs/GETTING_STARTED.md")
    engine = make_engine(settings.database_url.get_secret_value())
    with engine.connect() as connection:
        run(connection)
    engine.dispose()
