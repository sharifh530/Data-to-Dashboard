from uuid import uuid4

import pytest
from alembic import command
from dtd_api.database import check_schema, migrate, migration_config
from dtd_api.models import Artifact, Dataset, DatasetVersion, Project, Run, RunEvent, User
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def test_upgrade_downgrade_upgrade_and_no_schema_drift(db_engine: Engine) -> None:
    with db_engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.check(config)
        command.downgrade(config, "base")
    assert set(inspect(db_engine).get_table_names()) == {"alembic_version"}
    migrate(db_engine)
    check_schema(db_engine)


def test_database_rejects_cross_project_lineage(db_engine: Engine) -> None:
    with Session(db_engine) as db:
        user = User(auth_subject="test:" + str(uuid4()))
        db.add(user)
        db.flush()
        p1, p2 = Project(owner_id=user.id, name="One"), Project(owner_id=user.id, name="Two")
        db.add_all([p1, p2])
        db.flush()
        dataset = Dataset(project_id=p1.id, raw_key="one", raw_sha256="a" * 64, format="csv")
        db.add(dataset)
        db.flush()
        version = DatasetVersion(dataset_id=dataset.id, project_id=p1.id)
        db.add(version)
        db.flush()
        run = Run(project_id=p1.id, dataset_version_id=version.id)
        db.add(run)
        db.commit()
        bad_rows = [
            DatasetVersion(dataset_id=dataset.id, project_id=p2.id),
            Run(dataset_version_id=version.id, project_id=p2.id),
            Artifact(
                project_id=p2.id,
                run_id=run.id,
                kind="report",
                private_key="bad",
                sha256="b" * 64,
                size_bytes=1,
            ),
        ]
        for row in bad_rows:
            with pytest.raises(IntegrityError), db.begin_nested():
                db.add(row)
                db.flush()


def test_workflow_migration_preserves_existing_event_sequence(db_engine: Engine) -> None:
    with Session(db_engine) as db, db.begin():
        user = User(auth_subject="migration")
        db.add(user)
        db.flush()
        project = Project(owner_id=user.id, name="Existing")
        db.add(project)
        db.flush()
        dataset = Dataset(
            project_id=project.id, raw_key="fixture", raw_sha256="a" * 64, format="csv"
        )
        db.add(dataset)
        db.flush()
        version = DatasetVersion(dataset_id=dataset.id, project_id=project.id)
        db.add(version)
        db.flush()
        run = Run(project_id=project.id, dataset_version_id=version.id)
        db.add(run)
        db.flush()
        db.add(RunEvent(run_id=run.id, sequence=7, type="existing", payload={}))
    with db_engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.downgrade(config, "a0ae31772253")
        command.upgrade(config, "head")
        assert connection.scalar(text("SELECT event_sequence FROM runs")) == 7
