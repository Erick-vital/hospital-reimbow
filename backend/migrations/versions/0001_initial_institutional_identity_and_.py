"""Initial institutional identity and permissions

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('institutional_users',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('actor_key', sa.String(length=100), nullable=False),
    sa.Column('provider', sa.String(length=100), nullable=False),
    sa.Column('subject', sa.String(length=200), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('active', 'inactive')", name=op.f('ck_institutional_users_status')),
    sa.CheckConstraint('length(trim(actor_key)) > 0 AND length(trim(provider)) > 0 AND length(trim(subject)) > 0', name=op.f('ck_institutional_users_identity_not_empty')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_institutional_users')),
    sa.UniqueConstraint('actor_key', name=op.f('uq_institutional_users_actor_key')),
    sa.UniqueConstraint('provider', 'subject', name=op.f('uq_institutional_users_provider'))
    )
    op.create_table('permissions',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('code', sa.String(length=100), nullable=False),
    sa.CheckConstraint('length(trim(code)) > 0', name=op.f('ck_permissions_code_not_empty')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_permissions')),
    sa.UniqueConstraint('code', name=op.f('uq_permissions_code'))
    )
    op.create_table('roles',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('code', sa.String(length=100), nullable=False),
    sa.CheckConstraint('length(trim(code)) > 0', name=op.f('ck_roles_code_not_empty')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_roles')),
    sa.UniqueConstraint('code', name=op.f('uq_roles_code'))
    )
    op.create_table('role_permissions',
    sa.Column('role_id', sa.Uuid(), nullable=False),
    sa.Column('permission_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], name=op.f('fk_role_permissions_permission_id_permissions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_role_permissions_role_id_roles'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('role_id', 'permission_id', name=op.f('pk_role_permissions'))
    )
    op.create_table('user_roles',
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('role_id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_user_roles_role_id_roles'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['institutional_users.id'], name=op.f('fk_user_roles_user_id_institutional_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('user_id', 'role_id', name=op.f('pk_user_roles'))
    )


def downgrade() -> None:
    op.drop_table('user_roles')
    op.drop_table('role_permissions')
    op.drop_table('roles')
    op.drop_table('permissions')
    op.drop_table('institutional_users')
