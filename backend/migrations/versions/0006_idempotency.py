"""Reservas atómicas de altas V1/V2 y auditoría de replay.

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('idempotency_records',
        sa.Column('id', sa.Uuid(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('actor_id', sa.Uuid(), sa.ForeignKey('institutional_users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('operation', sa.String(40), nullable=False),
        sa.Column('key', sa.Uuid(), nullable=False),
        sa.Column('fingerprint', sa.String(64), nullable=False),
        sa.Column('state', sa.String(10), nullable=False, server_default='pending'),
        sa.Column('patient_id', sa.Uuid(), sa.ForeignKey('patients.id', ondelete='RESTRICT')),
        sa.Column('admission_id', sa.Uuid(), sa.ForeignKey('admissions.id', ondelete='RESTRICT')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('transaction_timestamp()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("transaction_timestamp() + interval '24 hours'")),
        sa.UniqueConstraint('actor_id', 'operation', 'key', name='uq_idempotency_actor_operation_key'),
        sa.CheckConstraint("operation IN ('v1.patients.create','v2.patients.create','v1.admissions.create','v2.admissions.create')", name='operation'),
        sa.CheckConstraint("fingerprint ~ '^[0-9a-f]{64}$'", name='fingerprint'),
        sa.CheckConstraint("(state = 'pending' AND patient_id IS NULL AND admission_id IS NULL) OR (state = 'completed' AND ((operation IN ('v1.patients.create','v2.patients.create') AND patient_id IS NOT NULL AND admission_id IS NULL) OR (operation IN ('v1.admissions.create','v2.admissions.create') AND admission_id IS NOT NULL AND patient_id IS NULL)))", name='resource'),
        sa.CheckConstraint("expires_at = created_at + interval '24 hours'", name='window'))
    op.execute("""CREATE FUNCTION check_idempotency_completed() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        IF EXISTS (SELECT 1 FROM idempotency_records WHERE id=NEW.id AND state='pending') THEN
            RAISE EXCEPTION 'Uncommitted idempotency reservation' USING ERRCODE='23514', CONSTRAINT='idempotency_completed';
        END IF;
        RETURN NULL;
    END $$""")
    op.execute("""CREATE CONSTRAINT TRIGGER idempotency_completed AFTER INSERT OR UPDATE ON idempotency_records
        DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_idempotency_completed()""")
    op.drop_constraint(op.f('ck_audit_events_action'), 'audit_events', type_='check')
    op.create_check_constraint('action', 'audit_events', "action IN ('patients.search','patients.create','patients.read','admissions.create','admissions.read','admissions.list','audit.read','identity.read','catalogs.read','patients.replay','admissions.replay')")


def downgrade():
    # Eventos de replay existentes impiden retirar su contrato silenciosamente.
    op.drop_constraint(op.f('ck_audit_events_action'), 'audit_events', type_='check')
    op.create_check_constraint('action', 'audit_events', "action IN ('patients.search','patients.create','patients.read','admissions.create','admissions.read','admissions.list','audit.read','identity.read','catalogs.read')")
    op.drop_table('idempotency_records')
    op.execute('DROP FUNCTION check_idempotency_completed()')
