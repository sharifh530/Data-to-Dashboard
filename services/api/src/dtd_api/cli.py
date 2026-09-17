import argparse

from sqlalchemy.orm import Session

from dtd_api.auth import issue_ticket
from dtd_api.database import make_engine
from dtd_api.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Local operator account provisioning")
    parser.add_argument(
        "--subject", required=True, help="Local account name; never an auth bypass header"
    )
    args = parser.parse_args()
    settings = Settings()
    if settings.environment != "local" or settings.database_url is None:
        raise SystemExit("Only local mode with a configured, migrated database is supported")
    engine = make_engine(settings.database_url.get_secret_value())
    try:
        with Session(engine) as session:
            token = issue_ticket(session, args.subject)
        print("Single-use sign-in token, valid for 5 minutes. Do not commit or share:")
        print(token)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
