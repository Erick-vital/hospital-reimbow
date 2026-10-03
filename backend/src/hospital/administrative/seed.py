"""Catálogos ficticios; nunca reemplaza nombres ni reactiva filas suspendidas."""
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from hospital.administrative.models import Service, Site


def seed_catalogs(session):
    # El llamador comparte la transacción con los permisos/identidades locales.
    for code, name in [('demo-central', 'Sede central ficticia'), ('demo-norte', 'Sede norte ficticia')]:
        session.execute(insert(Site).values(code=code, name=name).on_conflict_do_nothing(index_elements=['code']))
        site = session.scalar(select(Site).where(Site.code == code))
        for service_code, service_name in [('demo-emergency', 'Urgencias ficticias'), ('demo-general', 'Atención general ficticia')]:
            session.execute(insert(Service).values(site_id=site.id, code=service_code, name=service_name)
                            .on_conflict_do_nothing(index_elements=['site_id', 'code']))
