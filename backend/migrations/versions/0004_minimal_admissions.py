"""minimal admissions

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE admission_folio_seq AS bigint NO CYCLE")
    op.execute("""CREATE FUNCTION next_admission_folio() RETURNS text
        LANGUAGE sql VOLATILE AS $$
        SELECT 'EPI-' || lpad(n::text, greatest(12, length(n::text)), '0')
        FROM nextval('admission_folio_seq') AS n
        $$""")
    op.create_table('admissions',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('folio', sa.String(length=32), server_default=sa.text('next_admission_folio()'), nullable=False),
    sa.Column('patient_id', sa.Uuid(), nullable=False),
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='open', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.CheckConstraint("folio ~ '^EPI-[0-9]{12,}$'", name=op.f('ck_admissions_folio_format')),
    sa.CheckConstraint("status = 'open'", name=op.f('ck_admissions_status')),
    sa.CheckConstraint("type IN ('emergency', 'outpatient', 'inpatient')", name=op.f('ck_admissions_type')),
    sa.ForeignKeyConstraint(['created_by'], ['institutional_users.id'], name=op.f('fk_admissions_created_by_institutional_users'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_admissions_patient_id_patients'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_admissions')),
    sa.UniqueConstraint('folio', name=op.f('uq_admissions_folio'))
    )
    op.create_index('ix_admissions_patient_id_created_at_id', 'admissions', ['patient_id', 'created_at', 'id'], unique=False)



def downgrade() -> None:
    # Reversión explícita de desarrollo: elimina episodios.
    op.drop_index('ix_admissions_patient_id_created_at_id', table_name='admissions')
    op.drop_table('admissions')
    op.execute("DROP FUNCTION next_admission_folio()")
    op.execute("DROP SEQUENCE admission_folio_seq")
