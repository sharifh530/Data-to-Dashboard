import argparse
import signal
import threading

from dtd_api.database import check_schema, make_engine
from dtd_api.run_engine import work_once
from dtd_api.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Process fixed synthetic runs from PostgreSQL")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    if settings.environment != "local" or settings.database_url is None:
        raise SystemExit("Only local mode with a configured PostgreSQL database is supported")
    engine = make_engine(settings.database_url.get_secret_value())
    if engine.dialect.name != "postgresql":
        raise SystemExit("The durable worker requires PostgreSQL row locking")
    check_schema(engine)
    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    print("Synthetic worker ready. Generated execution remains disabled.", flush=True)
    try:
        while not stop.is_set():
            work_once(engine)
            if args.once:
                break
            stop.wait(0.5)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
