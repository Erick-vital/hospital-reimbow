"""Lecturas clínicas auditadas, sin tablas clínicas futuras.

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None

OLD_ACTIONS = "'patients.search','patients.create','patients.read','admissions.create','admissions.read','admissions.list','audit.read','identity.read','catalogs.read','patients.replay','admissions.replay'"
OLD_TYPES = "'patients','admissions','audit','identity','catalogs'"


def constraints(actions, types):
    op.drop_constraint(op.f('ck_audit_events_action'), 'audit_events', type_='check')
    op.create_check_constraint('action', 'audit_events', f'action IN ({actions})')
    op.drop_constraint(op.f('ck_audit_events_resource_type'), 'audit_events', type_='check')
    op.create_check_constraint('resource_type', 'audit_events', f'resource_type IS NULL OR resource_type IN ({types})')


def upgrade():
    constraints(OLD_ACTIONS + ",'clinical.attentions.read','clinical.context.read','clinical.catalogs.read'", OLD_TYPES + ",'clinical'")
    op.create_index('ix_admissions_open_created_at_id', 'admissions', ['created_at', 'id'], postgresql_where=sa.text("status = 'open'"))
    op.create_index('ix_admission_intakes_site_service', 'admission_intakes', ['site_id', 'service_id'])


def downgrade():
    # El CHECK impide retirar el contrato mientras existan eventos clínicos.
    constraints(OLD_ACTIONS, OLD_TYPES)
    op.drop_index('ix_admission_intakes_site_service', table_name='admission_intakes')
    op.drop_index('ix_admissions_open_created_at_id', table_name='admissions')
