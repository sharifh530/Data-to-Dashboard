"""Ephemeral browser-test backend; never started by the product API."""

import os
import threading
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn
from dtd_api.auth import issue_ticket
from dtd_api.database import migrate
from dtd_api.inspections import inspection_once
from dtd_api.main import create_app
from dtd_api.settings import Settings
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

Path(".local").mkdir(exist_ok=True)
temporary = TemporaryDirectory(prefix="web-test-", dir=".local")
# Separate connections are required when the inspection worker runs concurrently.
engine = create_engine("sqlite:///" + str(Path(temporary.name) / "metadata.sqlite"))


@event.listens_for(engine, "connect")
def constraints(connection, _):
    connection.execute("PRAGMA foreign_keys=ON")


migrate(engine)
ticket_path = Path(".local/web-test-ticket")
ticket_path.parent.mkdir(exist_ok=True)
with Session(engine) as db:
    ticket_path.write_text(issue_ticket(db, "browser-test"), encoding="utf-8")
inspection_image = os.environ.get("DTD_TEST_INSPECTION_IMAGE")
stop = threading.Event()


def inspect_pending():
    while not stop.wait(0.5):
        inspection_once(engine)


worker = threading.Thread(target=inspect_pending, daemon=True) if inspection_image else None
if worker:
    worker.start()
try:
    uvicorn.run(
        create_app(
            Settings(
                database_url=None,
                app_origin="http://127.0.0.1:4180",
                inspection_image=inspection_image,
            ),
            engine=engine,
        ),
        host="127.0.0.1",
        port=4180,
    )
finally:
    stop.set()
    if worker:
        worker.join(timeout=65)
    ticket_path.unlink(missing_ok=True)
    engine.dispose()
    temporary.cleanup()
