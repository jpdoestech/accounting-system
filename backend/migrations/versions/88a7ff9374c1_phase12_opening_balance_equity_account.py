"""phase12_opening_balance_equity_account

Revision ID: 88a7ff9374c1
Revises: 232148160c3d
Create Date: 2026-08-21 03:58:13.549549

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88a7ff9374c1'
down_revision: Union[str, None] = '232148160c3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('business_settings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('opening_balance_equity_account_id', sa.String(), nullable=True))
        batch_op.create_foreign_key(
            'fk_business_settings_opening_balance_equity_account', 'accounts', ['opening_balance_equity_account_id'], ['id']
        )


def downgrade() -> None:
    with op.batch_alter_table('business_settings', schema=None) as batch_op:
        batch_op.drop_constraint('fk_business_settings_opening_balance_equity_account', type_='foreignkey')
        batch_op.drop_column('opening_balance_equity_account_id')
