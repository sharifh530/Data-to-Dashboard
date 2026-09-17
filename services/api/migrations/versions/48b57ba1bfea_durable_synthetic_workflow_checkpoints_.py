"""durable synthetic workflow checkpoints and leases

Revision ID: 48b57ba1bfea
Revises: a0ae31772253
"""

import sqlalchemy as sa
from alembic import op

revision = "48b57ba1bfea"
down_revision = "a0ae31772253"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "work_items",
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("token", sa.String(length=36), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state IN ('pending','leased','done')", name=op.f("ck_work_items_state")
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], name=op.f("fk_work_items_run_id_runs")),
        sa.PrimaryKeyConstraint("run_id", name=op.f("pk_work_items")),
    )
    op.create_index(
        op.f("ix_work_items_lease_expires_at"), "work_items", ["lease_expires_at"], unique=False
    )
    op.create_index(op.f("ix_work_items_state"), "work_items", ["state"], unique=False)
    op.add_column(
        "runs", sa.Column("event_sequence", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column("runs", sa.Column("checkpoint", sa.JSON(), server_default="{}", nullable=False))
    op.add_column("runs", sa.Column("result", sa.JSON(), nullable=True))
    op.add_column("runs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("runs", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE runs SET event_sequence = "
        "COALESCE((SELECT MAX(sequence) FROM run_events WHERE run_events.run_id = runs.id), 0)"
    )


def downgrade():
    op.drop_column("runs", "finished_at")
    op.drop_column("runs", "started_at")
    op.drop_column("runs", "result")
    op.drop_column("runs", "checkpoint")
    op.drop_column("runs", "event_sequence")
    op.drop_index(op.f("ix_work_items_state"), table_name="work_items")
    op.drop_index(op.f("ix_work_items_lease_expires_at"), table_name="work_items")
    op.drop_table("work_items")
