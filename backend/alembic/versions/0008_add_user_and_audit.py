from alembic import op
import sqlalchemy as sa

revision = '0008_add_user_and_audit'
down_revision = '0007_add_trip_commission_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('password_hash', sa.String(length=128), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    op.execute(
        "INSERT INTO users (username, password_hash, role) "
        "VALUES ('admin', '$2b$12$ttum8dxqome/azGjJyGiCewJvMjOcHbbd6rs23ufRkUpyoa7EzhTe', 'ADMIN')"
    )

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('details', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('users')
