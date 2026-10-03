"""administrative_v2

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(FUNCTIONS)
    op.create_table('admission_sites',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_admission_sites')),
    sa.UniqueConstraint('code', name=op.f('uq_admission_sites_code'))
    )
    op.create_table('admission_services',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('site_id', sa.Uuid(), nullable=False),
    sa.Column('code', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['admission_sites.id'], name=op.f('fk_admission_services_site_id_admission_sites'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_admission_services')),
    sa.UniqueConstraint('site_id', 'code', name=op.f('uq_admission_services_site_id')),
    sa.UniqueConstraint('site_id', 'id', name='uq_admission_services_site_id_id')
    )
    op.create_index(op.f('ix_admission_services_site_id'), 'admission_services', ['site_id'], unique=False)
    op.create_table('patient_administrative_profiles',
    sa.Column('patient_id', sa.Uuid(), nullable=False),
    sa.Column('is_unidentified', sa.Boolean(), nullable=False),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.CheckConstraint('v2_profile_valid(data) IS TRUE', name=op.f('ck_patient_administrative_profiles_profile_valid')),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_patient_administrative_profiles_patient_id_patients'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('patient_id', name=op.f('pk_patient_administrative_profiles'))
    )
    op.create_table('admission_intakes',
    sa.Column('admission_id', sa.Uuid(), nullable=False),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('admitted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('site_id', sa.Uuid(), nullable=True),
    sa.Column('service_id', sa.Uuid(), nullable=True),
    sa.CheckConstraint("(data->'site_id'->>'value')::uuid IS NOT DISTINCT FROM site_id AND (data->'service_id'->>'value')::uuid IS NOT DISTINCT FROM service_id", name=op.f('ck_admission_intakes_catalog_values')),
    sa.CheckConstraint('admitted_at IS NULL OR admitted_at <= clock_timestamp()', name=op.f('ck_admission_intakes_past_admission')),
    sa.CheckConstraint('service_id IS NULL OR site_id IS NOT NULL', name=op.f('ck_admission_intakes_service_site')),
    sa.CheckConstraint('v2_intake_valid(data) IS TRUE', name=op.f('ck_admission_intakes_intake_valid')),
    sa.ForeignKeyConstraint(['admission_id'], ['admissions.id'], name=op.f('fk_admission_intakes_admission_id_admissions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['service_id'], ['admission_services.id'], name=op.f('fk_admission_intakes_service_id_admission_services'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['site_id', 'service_id'], ['admission_services.site_id', 'admission_services.id'], name='fk_admission_intakes_site_service', ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['site_id'], ['admission_sites.id'], name=op.f('fk_admission_intakes_site_id_admission_sites'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('admission_id', name=op.f('pk_admission_intakes'))
    )
    op.create_table('patient_administrative_items',
    sa.Column('patient_id', sa.Uuid(), nullable=False),
    sa.Column('kind', sa.String(length=30), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.CheckConstraint("kind IN ('phones','addresses','emergency_contacts')", name=op.f('ck_patient_administrative_items_kind')),
    sa.CheckConstraint('position BETWEEN 0 AND 9', name=op.f('ck_patient_administrative_items_position')),
    sa.CheckConstraint('v2_item_valid(kind, data) IS TRUE', name=op.f('ck_patient_administrative_items_item_valid')),
    sa.ForeignKeyConstraint(['patient_id'], ['patient_administrative_profiles.patient_id'], name=op.f('fk_patient_administrative_items_patient_id_patient_administrative_profiles'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('patient_id', 'kind', 'position', name=op.f('pk_patient_administrative_items'))
    )
    op.create_table('patient_identity_verifications',
    sa.Column('patient_id', sa.Uuid(), nullable=False),
    sa.Column('verified_by', sa.Uuid(), nullable=False),
    sa.Column('verified_at', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patient_administrative_profiles.patient_id'], name=op.f('fk_patient_identity_verifications_patient_id_patient_administrative_profiles'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['verified_by'], ['institutional_users.id'], name=op.f('fk_patient_identity_verifications_verified_by_institutional_users'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('patient_id', name=op.f('pk_patient_identity_verifications'))
    )
    op.create_table('patient_verification_evidence',
    sa.Column('patient_id', sa.Uuid(), nullable=False),
    sa.Column('field', sa.String(length=20), nullable=False),
    sa.Column('source_kind', sa.String(length=30), nullable=False),
    sa.Column('source_reference', sa.String(length=200), nullable=False),
    sa.Column('snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.CheckConstraint("field IN ('full_name','birth_date','CURP')", name=op.f('ck_patient_verification_evidence_field')),
    sa.CheckConstraint("jsonb_typeof(snapshot) = 'object'", name=op.f('ck_patient_verification_evidence_snapshot')),
    sa.CheckConstraint("source_kind IN ('official_document','institutional_document')", name=op.f('ck_patient_verification_evidence_source_kind')),
    sa.CheckConstraint('length(trim(source_reference)) BETWEEN 1 AND 200', name=op.f('ck_patient_verification_evidence_source_reference')),
    sa.ForeignKeyConstraint(['patient_id'], ['patient_identity_verifications.patient_id'], name=op.f('fk_patient_verification_evidence_patient_id_patient_identity_verifications'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('patient_id', 'field', name=op.f('pk_patient_verification_evidence'))
    )
    op.drop_constraint(op.f('ck_audit_events_action'), 'audit_events', type_='check')
    op.create_check_constraint(op.f('ck_audit_events_action'), 'audit_events', "action IN ('patients.search','patients.create','patients.read','admissions.create','admissions.read','admissions.list','audit.read','identity.read','catalogs.read')")
    op.drop_constraint(op.f('ck_audit_events_resource_type'), 'audit_events', type_='check')
    op.create_check_constraint(op.f('ck_audit_events_resource_type'), 'audit_events', "resource_type IS NULL OR resource_type IN ('patients','admissions','audit','identity','catalogs')")
    op.execute(TRIGGERS)


def downgrade() -> None:
    for table in ('patients', 'patient_identifiers', 'patient_administrative_profiles', 'patient_administrative_items', 'patient_identity_verifications', 'patient_verification_evidence'):
        op.execute(f'DROP TRIGGER v2_patient_integrity ON {table}')
    for table in ('admissions', 'admission_intakes'):
        op.execute(f'DROP TRIGGER v2_intake_integrity ON {table}')
    op.execute('DROP FUNCTION v2_check_patient(); DROP FUNCTION v2_check_intake()')
    op.drop_constraint(op.f('ck_audit_events_action'), 'audit_events', type_='check')
    op.create_check_constraint(op.f('ck_audit_events_action'), 'audit_events', "action IN ('patients.search','patients.create','patients.read','admissions.create','admissions.read','admissions.list','audit.read','identity.read')")
    op.drop_constraint(op.f('ck_audit_events_resource_type'), 'audit_events', type_='check')
    op.create_check_constraint(op.f('ck_audit_events_resource_type'), 'audit_events', "resource_type IS NULL OR resource_type IN ('patients','admissions','audit','identity')")
    op.drop_table('patient_verification_evidence')
    op.drop_table('patient_identity_verifications')
    op.drop_table('patient_administrative_items')
    op.drop_table('admission_intakes')
    op.drop_table('patient_administrative_profiles')
    op.drop_index(op.f('ix_admission_services_site_id'), table_name='admission_services')
    op.drop_table('admission_services')
    op.drop_table('admission_sites')
    op.execute('DROP FUNCTION v2_profile_valid(jsonb); DROP FUNCTION v2_intake_valid(jsonb); DROP FUNCTION v2_item_valid(text,jsonb); DROP FUNCTION v2_description_valid(jsonb); DROP FUNCTION v2_absent_valid(jsonb,text,integer); DROP FUNCTION v2_text_valid(jsonb,integer); DROP FUNCTION v2_keys(jsonb,text[])')


FUNCTIONS = r"""
CREATE FUNCTION v2_keys(j jsonb, keys text[]) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
 SELECT COALESCE(jsonb_typeof(j)='object' AND j ?& keys AND (j - keys)='{}'::jsonb, false)
$$;
CREATE FUNCTION v2_text_valid(j jsonb, maximum integer) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
 SELECT COALESCE(jsonb_typeof(j)='string' AND length(trim(j #>> '{}')) BETWEEN 1 AND maximum, false)
$$;
CREATE FUNCTION v2_absent_valid(j jsonb, typ text, maximum integer DEFAULT 1000) RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$
BEGIN
 IF NOT v2_keys(j, ARRAY['state','value']) THEN RETURN false; END IF;
 IF j->>'state' IN ('unknown','not_provided','not_applicable') THEN RETURN j->'value'='null'::jsonb; END IF;
 IF (j->>'state') IS DISTINCT FROM 'known' OR j->'value'='null'::jsonb THEN RETURN false; END IF;
 IF typ='string' THEN RETURN v2_text_valid(j->'value', maximum); END IF;
 RETURN COALESCE(jsonb_typeof(j->'value')=typ, false);
END $$;
CREATE FUNCTION v2_description_valid(j jsonb) RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE a jsonb;
BEGIN
 IF NOT v2_keys(j, ARRAY['apparent_sex','estimated_age','identifying_features','origin','transferred_by']) THEN RETURN false; END IF;
 IF NOT (v2_absent_valid(j->'apparent_sex','string',100) AND v2_absent_valid(j->'identifying_features','string',1000)
 AND v2_absent_valid(j->'origin','string',200) AND v2_absent_valid(j->'transferred_by','string',200)
 AND v2_absent_valid(j->'estimated_age','object')) THEN RETURN false; END IF;
 IF j->'estimated_age'->>'state' <> 'known' THEN RETURN true; END IF;
 a := j->'estimated_age'->'value';
 RETURN v2_keys(a, ARRAY['min_years','max_years'])
 AND (a->>'min_years') ~ '^[0-9]{1,3}$' AND (a->>'max_years') ~ '^[0-9]{1,3}$'
 AND jsonb_typeof(a->'min_years')='number' AND jsonb_typeof(a->'max_years')='number'
 AND (a->>'min_years')::int BETWEEN 0 AND (a->>'max_years')::int AND (a->>'max_years')::int <= 150;
EXCEPTION WHEN invalid_text_representation THEN RETURN false;
END $$;
CREATE FUNCTION v2_profile_valid(j jsonb) RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE k text;
BEGIN
 IF NOT v2_keys(j, ARRAY['registered_sex','nationality','collection_states','identity_field_states','unidentified_description']) THEN RETURN false; END IF;
 IF NOT (v2_absent_valid(j->'registered_sex','string',100) AND v2_absent_valid(j->'nationality','string',100)
 AND v2_description_valid(j->'unidentified_description')
 AND v2_keys(j->'collection_states',ARRAY['phones','addresses','emergency_contacts'])
 AND v2_keys(j->'identity_field_states',ARRAY['given_names','family_name','second_family_name','birth_date'])) THEN RETURN false; END IF;
 FOR k IN SELECT value FROM jsonb_each_text(j->'collection_states') UNION ALL SELECT value FROM jsonb_each_text(j->'identity_field_states') LOOP
   IF k IS NULL OR k NOT IN ('known','unknown','not_provided','not_applicable') THEN RETURN false; END IF;
 END LOOP;
 RETURN true;
END $$;
CREATE FUNCTION v2_item_valid(kind text, j jsonb) RETURNS boolean LANGUAGE plpgsql IMMUTABLE AS $$
DECLARE k text; v jsonb; found boolean := false; maximum integer;
BEGIN
 IF jsonb_typeof(j) <> 'object' THEN RETURN false; END IF;
 IF kind='phones' THEN
   RETURN v2_keys(j, ARRAY['kind','number']) AND j->>'kind' IN ('personal','fixed','work','other') AND v2_text_valid(j->'number',40);
 ELSIF kind='emergency_contacts' THEN
   RETURN v2_keys(j,ARRAY['name','relationship','phone']) AND v2_text_valid(j->'name',200)
     AND v2_absent_valid(j->'relationship','string',100) AND v2_absent_valid(j->'phone','string',40);
 ELSIF kind='addresses' THEN
   IF NOT v2_keys(j,ARRAY['kind','street','exterior','interior','neighborhood','postal_code','municipality','state','country','references'])
     OR j->>'kind' NOT IN ('principal','temporary','fiscal','correspondence','other') THEN RETURN false; END IF;
   FOR k,v IN SELECT key,value FROM jsonb_each(j - 'kind') LOOP
     IF v <> 'null'::jsonb THEN
       maximum := CASE k WHEN 'postal_code' THEN 20 WHEN 'references' THEN 500 ELSE 200 END;
       IF NOT v2_text_valid(v,maximum) THEN RETURN false; END IF;
       found := true;
     END IF;
   END LOOP;
   RETURN found;
 END IF;
 RETURN false;
END $$;
CREATE FUNCTION v2_intake_valid(j jsonb) RETURNS boolean LANGUAGE sql IMMUTABLE AS $$
 SELECT v2_keys(j, ARRAY['admitted_at','site_id','service_id','origin','reason_for_visit'])
 AND v2_absent_valid(j->'admitted_at','string',50) AND v2_absent_valid(j->'site_id','string',36)
 AND v2_absent_valid(j->'service_id','string',36) AND v2_absent_valid(j->'origin','string',200)
 AND v2_absent_valid(j->'reason_for_visit','string',1000)
$$;
"""

TRIGGERS = r"""
CREATE FUNCTION v2_check_patient() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE pid uuid; p patients%ROWTYPE; profile patient_administrative_profiles%ROWTYPE;
        k text; v jsonb; expected jsonb; e patient_verification_evidence%ROWTYPE; fields text[];
BEGIN
 IF TG_TABLE_NAME <> 'patients' THEN
   IF TG_OP='UPDATE' AND NEW.patient_id IS DISTINCT FROM OLD.patient_id THEN
     RAISE EXCEPTION 'V2 parent is immutable' USING ERRCODE='23514';
   END IF;
 END IF;
 IF TG_TABLE_NAME='patients' THEN pid := COALESCE(NEW.id,OLD.id);
 ELSE pid := COALESCE(NEW.patient_id,OLD.patient_id); END IF;
 SELECT * INTO p FROM patients WHERE id=pid FOR UPDATE;
 SELECT * INTO profile FROM patient_administrative_profiles WHERE patient_id=pid;
 IF NOT FOUND THEN
   IF TG_TABLE_NAME='patient_administrative_profiles' AND TG_OP='DELETE' THEN
     RAISE EXCEPTION 'V2 profile required' USING ERRCODE='23514';
   END IF;
   RETURN NULL;
 END IF;
 FOR k IN SELECT jsonb_object_keys(profile.data->'identity_field_states') LOOP
   IF ((profile.data->'identity_field_states'->>k)='known') IS DISTINCT FROM (to_jsonb(p)->k <> 'null'::jsonb) THEN
     RAISE EXCEPTION 'V2 identity state mismatch' USING ERRCODE='23514';
   END IF;
 END LOOP;
 IF profile.is_unidentified AND (p.identity_status <> 'provisional' OR p.given_names IS NOT NULL OR p.family_name IS NOT NULL
 OR p.second_family_name IS NOT NULL OR p.birth_date IS NOT NULL OR EXISTS(SELECT 1 FROM patient_identifiers WHERE patient_id=pid)) THEN
   RAISE EXCEPTION 'V2 unidentified identity mismatch' USING ERRCODE='23514';
 END IF;
 IF NOT profile.is_unidentified AND EXISTS(SELECT 1 FROM jsonb_each(profile.data->'unidentified_description') WHERE value->>'state' <> 'not_provided') THEN
   RAISE EXCEPTION 'V2 descriptor requires unidentified' USING ERRCODE='23514';
 END IF;
 IF EXISTS(SELECT 1 FROM patient_administrative_items WHERE patient_id=pid AND profile.data->'collection_states'->>kind <> 'known') THEN
   RAISE EXCEPTION 'V2 collection state mismatch' USING ERRCODE='23514';
 END IF;
 SELECT array_agg(field) INTO fields FROM patient_verification_evidence WHERE patient_id=pid;
 IF p.identity_status='verified' THEN
   IF NOT EXISTS(SELECT 1 FROM patient_identity_verifications WHERE patient_id=pid)
   OR NOT COALESCE('full_name'=ANY(fields) AND ('birth_date'=ANY(fields) OR 'CURP'=ANY(fields)),false) THEN
     RAISE EXCEPTION 'V2 verification incomplete' USING ERRCODE='23514';
   END IF;
 ELSIF EXISTS(SELECT 1 FROM patient_identity_verifications WHERE patient_id=pid) THEN
   RAISE EXCEPTION 'V2 verification status mismatch' USING ERRCODE='23514';
 END IF;
 FOR e IN SELECT * FROM patient_verification_evidence WHERE patient_id=pid LOOP
   CASE e.field
   WHEN 'full_name' THEN expected := jsonb_build_object('given_names',p.given_names,'family_name',p.family_name,'second_family_name',p.second_family_name);
   WHEN 'birth_date' THEN
     IF p.birth_date IS NULL THEN RAISE EXCEPTION 'V2 absent birth' USING ERRCODE='23514'; END IF;
     expected := jsonb_build_object('birth_date',p.birth_date);
   WHEN 'CURP' THEN
     IF (SELECT count(*) FROM patient_identifiers WHERE patient_id=pid AND system='CURP') <> 1 THEN
       RAISE EXCEPTION 'V2 ambiguous CURP' USING ERRCODE='23514'; END IF;
     SELECT jsonb_build_object('CURP',value) INTO expected FROM patient_identifiers WHERE patient_id=pid AND system='CURP';
   END CASE;
   IF e.snapshot IS DISTINCT FROM expected THEN RAISE EXCEPTION 'V2 evidence mismatch' USING ERRCODE='23514'; END IF;
 END LOOP;
 RETURN NULL;
END $$;
DO $$ DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['patients','patient_identifiers','patient_administrative_profiles','patient_administrative_items','patient_identity_verifications','patient_verification_evidence'] LOOP
   EXECUTE format('CREATE CONSTRAINT TRIGGER v2_patient_integrity AFTER INSERT OR UPDATE OR DELETE ON %I DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION v2_check_patient()',t);
 END LOOP;
END $$;
CREATE FUNCTION v2_check_intake() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE aid uuid; a admissions%ROWTYPE; i admission_intakes%ROWTYPE; active_site boolean; active_service boolean;
BEGIN
 IF TG_TABLE_NAME='admission_intakes' THEN
   IF TG_OP='UPDATE' AND NEW.admission_id IS DISTINCT FROM OLD.admission_id THEN
     RAISE EXCEPTION 'V2 intake parent is immutable' USING ERRCODE='23514';
   END IF;
 END IF;
 IF TG_TABLE_NAME='admissions' THEN aid := COALESCE(NEW.id,OLD.id);
 ELSE aid := COALESCE(NEW.admission_id,OLD.admission_id); END IF;
 SELECT * INTO a FROM admissions WHERE id=aid FOR UPDATE;
 SELECT * INTO i FROM admission_intakes WHERE admission_id=aid;
 IF NOT FOUND THEN
   IF TG_TABLE_NAME='admission_intakes' AND TG_OP='DELETE' THEN RAISE EXCEPTION 'V2 intake required' USING ERRCODE='23514'; END IF;
   RETURN NULL;
 END IF;
 IF a.type <> 'emergency' AND (i.admitted_at IS NULL OR i.site_id IS NULL OR i.service_id IS NULL) THEN
   RAISE EXCEPTION 'V2 required intake' USING ERRCODE='23514';
 END IF;
 IF (i.data->'admitted_at'->>'value')::timestamptz IS DISTINCT FROM i.admitted_at OR
   (i.admitted_at IS NOT NULL AND NOT (i.data->'admitted_at'->>'value' ~ '(Z|[+-][0-9]{2}:[0-9]{2})$')) THEN
   RAISE EXCEPTION 'V2 admission time mismatch' USING ERRCODE='23514';
 END IF;
 -- Suspender catálogos no invalida ingresos históricos. En nuevas escrituras
 -- de intake, bloquear las filas durante la comprobación de actividad.
 IF TG_TABLE_NAME='admission_intakes' AND TG_OP <> 'DELETE' THEN
   IF i.site_id IS NOT NULL THEN
     SELECT active INTO active_site FROM admission_sites WHERE id=i.site_id FOR SHARE;
     IF active_site IS DISTINCT FROM true THEN RAISE EXCEPTION 'V2 inactive site' USING ERRCODE='23514'; END IF;
   END IF;
   IF i.service_id IS NOT NULL THEN
     SELECT active INTO active_service FROM admission_services WHERE id=i.service_id AND site_id=i.site_id FOR SHARE;
     IF active_service IS DISTINCT FROM true THEN RAISE EXCEPTION 'V2 inactive service' USING ERRCODE='23514'; END IF;
   END IF;
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER v2_intake_integrity AFTER INSERT OR UPDATE OR DELETE ON admissions DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION v2_check_intake();
CREATE CONSTRAINT TRIGGER v2_intake_integrity AFTER INSERT OR UPDATE OR DELETE ON admission_intakes DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION v2_check_intake();
"""
