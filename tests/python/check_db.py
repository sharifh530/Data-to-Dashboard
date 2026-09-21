import os

from dtd_api.models import Run, StageAttempt, WorkItem
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

engine = create_engine(os.environ.get("DTD_TEST_DATABASE_URL", "sqlite:///test.db"))

with Session(engine) as db:
    run = db.scalar(select(Run).order_by(Run.created_at.desc()).limit(1))
    if run:
        print(f"Run {run.id}: status={run.status} stage={run.stage} config={run.config}")
        print(f"Checkpoint: {run.checkpoint}")
        job = db.get(WorkItem, run.id)
        print(f"Job state={job.state if job else 'none'}")

        attempts = db.scalars(select(StageAttempt).where(StageAttempt.run_id == run.id)).all()
        for a in attempts:
            print(f"Attempt: {a.stage} {a.status}")
    else:
        print("No runs found")
