"""Start a project-owned loopback PostgreSQL cluster. Never touch a system cluster."""

import argparse
import os
import secrets
import subprocess
from pathlib import Path

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--bin", type=Path, required=True)
parser.add_argument("--stop", action="store_true")
args = parser.parse_args()
folder = ROOT / ".local" / "postgres"
data = folder / "data"
flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
suffix = ".exe" if os.name == "nt" else ""


def pg(name, *arguments, check=True):
    # File redirection avoids Windows descendants inheriting a captured pipe and preventing EOF.
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "bootstrap.log").open("a", encoding="utf-8") as log:
        return subprocess.run(
            [str(args.bin / (name + suffix)), *map(str, arguments)],
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=flags,
            check=check,
            timeout=60,
        )


if args.stop:
    if not (data / "PG_VERSION").exists():
        raise SystemExit("No project cluster exists.")
    pg("pg_ctl", "-D", data, "-m", "fast", "stop")
    raise SystemExit("Project PostgreSQL stopped.")

folder.mkdir(parents=True, exist_ok=True)
password_file = folder / "password"
if not password_file.exists():
    password_file.write_text(secrets.token_hex(32), encoding="utf-8")
password = password_file.read_text(encoding="utf-8").strip()
if not (data / "PG_VERSION").exists():
    pg(
        "initdb",
        "-D",
        data,
        "-U",
        "dtd",
        "--auth=scram-sha-256",
        "--pwfile",
        password_file,
        "--encoding=UTF8",
        "--locale=C",
    )
if pg("pg_ctl", "-D", data, "status", check=False).returncode != 0:
    pg("pg_ctl", "-D", data, "-l", folder / "server.log", "-o", "-p 55432 -h 127.0.0.1", "start")
with psycopg.connect(
    host="127.0.0.1", port=55432, user="dtd", password=password, dbname="postgres", autocommit=True
) as connection:
    for name in ("dtd", "dtd_test"):
        if not connection.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,)).fetchone():
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
env_file = ROOT / ".env"
existing = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
if "DTD_DATABASE_URL=" not in existing:
    with env_file.open("a", encoding="utf-8") as handle:
        handle.write(
            f"\nDTD_DATABASE_URL=postgresql+psycopg://dtd:{password}@127.0.0.1:55432/dtd\n"
        )
print("Project PostgreSQL ready on 127.0.0.1:55432; dtd/dtd_test databases available.")
print("Connection configuration is in ignored .env; credentials are not printed.")
