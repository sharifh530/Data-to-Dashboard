"""selected dataset version

Revision ID: fcae1f133cd7
Revises: ca79f5d67de3
"""

import sqlalchemy as sa
from alembic import op

revision = "fcae1f133cd7"
down_revision = "ca79f5d67de3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("inspections") as batch:
        batch.add_column(sa.Column("selected_version_id", sa.String(length=36), nullable=True))
        batch.create_foreign_key(
            op.f("fk_inspections_selected_version_id_dataset_versions"),
            "dataset_versions",
            ["selected_version_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("inspections") as batch:
        batch.drop_constraint(
            op.f("fk_inspections_selected_version_id_dataset_versions"), type_="foreignkey"
        )
        batch.drop_column("selected_version_id")
