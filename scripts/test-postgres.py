"""Run tests against isolated schemas in the project-owned test database."""

import os
import subprocess
import sys

from dtd_api.settings import Settings
from sqlalchemy.engine import make_url

settings = Settings()
if "DTD_TEST_DATABASE_URL" in os.environ:
    environment = dict(os.environ)
else:
    if settings.database_url is None:
        raise SystemExit("Configure the project database first; see docs/GETTING_STARTED.md")
    url = make_url(settings.database_url.get_secret_value())
    if url.host != "127.0.0.1" or url.port != 55432 or url.database != "dtd":
        raise SystemExit("Automatic test URL is limited to the project-owned local cluster")
    environment = {
        **os.environ,
        "DTD_TEST_DATABASE_URL": url.set(database="dtd_test").render_as_string(hide_password=False),
    }
result = subprocess.run([sys.executable, "-m", "pytest"], env=environment, check=False)
raise SystemExit(result.returncode)
