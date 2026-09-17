"""Ephemeral browser-test backend; never started by the product API."""

from pathlib import Path

import uvicorn
from dtd_api.auth import issue_ticket
from dtd_api.database import make_engine, migrate
from dtd_api.main import create_app
from dtd_api.settings import Settings
from sqlalchemy.orm import Session

engine = make_engine("sqlite://")
migrate(engine)
ticket_path = Path(".local/web-test-ticket")
ticket_path.parent.mkdir(exist_ok=True)
with Session(engine) as db:
    ticket_path.write_text(issue_ticket(db, "browser-test"), encoding="utf-8")
try:
    uvicorn.run(
        create_app(Settings(database_url=None, app_origin="http://127.0.0.1:4180"), engine=engine),
        host="127.0.0.1",
        port=4180,
    )
finally:
    ticket_path.unlink(missing_ok=True)
    engine.dispose()
