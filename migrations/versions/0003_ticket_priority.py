"""add ticket priority

Revision ID: 0003_ticket_priority
Revises: 0002_security_events
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_ticket_priority"
down_revision = "0002_security_events"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "tickets",
        sa.Column(
            "priority",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'Normal'"),
        ),
    )


def downgrade():
    op.drop_column("tickets", "priority")