"""patients and prior searches

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE patient_folio_seq AS bigint NO CYCLE")
    op.execute("""CREATE FUNCTION next_patient_folio() RETURNS text
        LANGUAGE sql VOLATILE AS $$
        SELECT 'PAC-' || lpad(n::text, greatest(12, length(n::text)), '0')
        FROM nextval('patient_folio_seq') AS n
        $$""")
    op.create_table('patient_searches',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('actor_id', sa.Uuid(), nullable=False),
    sa.Column('filters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), server_default=sa.text("(clock_timestamp() + '00:15:00'::interval)"), nullable=False),
    sa.CheckConstraint("jsonb_typeof(filters) = 'object'", name=op.f('ck_patient_searches_filters_object')),
    sa.CheckConstraint('expires_at > created_at', name=op.f('ck_patient_searches_expiry')),
    sa.ForeignKeyConstraint(['actor_id'], ['institutional_users.id'], name=op.f('fk_patient_searches_actor_id_institutional_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_patient_searches'))
    )
    op.create_index('ix_patient_searches_expires_at', 'patient_searches', ['expires_at'], unique=False)
    op.create_table('patients',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('folio', sa.String(length=32), server_default=sa.text('next_patient_folio()'), nullable=False),
    sa.Column('identity_status', sa.String(length=20), nullable=False),
    sa.Column('given_names', sa.String(length=100), nullable=True),
    sa.Column('family_name', sa.String(length=100), nullable=True),
    sa.Column('second_family_name', sa.String(length=100), nullable=True),
    sa.Column('birth_date', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.CheckConstraint("birth_date IS NULL OR birth_date <= (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')::date", name=op.f('ck_patients_birth_date')),
    sa.CheckConstraint("folio ~ '^PAC-[0-9]{12,}$'", name=op.f('ck_patients_folio_format')),
    sa.CheckConstraint("identity_status <> 'verified' OR given_names IS NOT NULL", name=op.f('ck_patients_verified_name')),
    sa.CheckConstraint("identity_status IN ('provisional', 'verified')", name=op.f('ck_patients_identity_status')),
    sa.CheckConstraint('(given_names IS NULL OR length(trim(given_names)) > 0) AND (family_name IS NULL OR length(trim(family_name)) > 0) AND (second_family_name IS NULL OR length(trim(second_family_name)) > 0)', name=op.f('ck_patients_names_not_empty')),
    sa.ForeignKeyConstraint(['created_by'], ['institutional_users.id'], name=op.f('fk_patients_created_by_institutional_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_patients')),
    sa.UniqueConstraint('folio', name=op.f('uq_patients_folio'))
    )
    op.create_index('ix_patients_created_at_id', 'patients', ['created_at', 'id'], unique=False)
    op.create_table('patient_identifiers',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('patient_id', sa.Uuid(), nullable=False),
    sa.Column('system', sa.String(length=10), nullable=False),
    sa.Column('value', sa.String(length=64), nullable=False),
    sa.CheckConstraint("(system = 'CURP' AND value ~ '^[A-Z0-9]{18}$') OR (system = 'TEST' AND value ~ '^[A-Z0-9_-]{1,64}$')", name=op.f('ck_patient_identifiers_identifier_format')),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_patient_identifiers_patient_id_patients'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_patient_identifiers')),
    sa.UniqueConstraint('system', 'value', name='uq_patient_identifiers_system_value')
    )
    op.create_index(op.f('ix_patient_identifiers_patient_id'), 'patient_identifiers', ['patient_id'], unique=False)



def downgrade() -> None:
    # Reversión explícita de desarrollo: elimina estas entidades.
    op.drop_index(op.f('ix_patient_identifiers_patient_id'), table_name='patient_identifiers')
    op.drop_table('patient_identifiers')
    op.drop_index('ix_patients_created_at_id', table_name='patients')
    op.drop_table('patients')
    op.drop_index('ix_patient_searches_expires_at', table_name='patient_searches')
    op.drop_table('patient_searches')
    op.execute("DROP FUNCTION next_patient_folio()")
    op.execute("DROP SEQUENCE patient_folio_seq")
