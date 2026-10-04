import { useState } from 'react'
import type { PageResult } from '../api/contracts'
import type { Session } from '../identity/session'
import { Heading } from '../components/Heading'
import { ErrorNotice, Loading } from '../components/Feedback'
import { useResource } from '../components/useResource'

interface AuditEvent { id: string; action: string; result: string; resource_id: string | null; actor_id: string | null; created_at: string; request_id: string }
export function AuditView({ session }: { session: Session }) {
  const [query, setQuery] = useState(new URLSearchParams({ limit: '20' }))
  const [offset, setOffset] = useState(0)
  const [run, setRun] = useState(0)
  const { data, error } = useResource<PageResult<AuditEvent>>(session, `/api/v1/audit?${query}&offset=${offset}`, run)
  return <section className="card"><Heading>Auditoría</Heading><p className="lead">Acceso autorizado a eventos del recorrido. Filtra por UUID de paciente o episodio para comprobar altas y repeticiones.</p>
    <form className="search-form" onSubmit={e => { e.preventDefault(); const form = new FormData(e.currentTarget); const params = new URLSearchParams({ limit: '20' }); for (const key of ['action', 'resource_id']) { const value = String(form.get(key) ?? '').trim(); if (value) params.set(key, value) } setOffset(0); setQuery(params); setRun(value => value + 1) }}>
      <label>Acción<select aria-label="Acción" name="action"><option value="">Todas</option>{['patients.create', 'admissions.create', 'patients.replay', 'admissions.replay', 'patients.search', 'patients.read', 'admissions.read', 'admissions.list', 'catalogs.read', 'audit.read', 'identity.read', 'clinical.attentions.read', 'clinical.context.read', 'clinical.catalogs.read'].map(action => <option key={action}>{action}</option>)}</select></label>
      <label>UUID del recurso<input name="resource_id" pattern="[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}" /></label><button className="button" type="submit">Consultar auditoría</button>
    </form>{error ? <ErrorNotice error={error} /> : !data ? <Loading message="Consultando auditoría…" /> : <><p role="status">{data.total} eventos</p><ul className="record-list audit-list">{data.items.map(event => <li key={event.id}><div><strong>{event.action} · {event.result}</strong><p>{new Date(event.created_at).toLocaleString('es-MX')}</p><p>Recurso: {event.resource_id || 'Sin recurso'}</p><p>Actor: {event.actor_id || 'Sin actor'}</p><p>Solicitud: {event.request_id}</p></div></li>)}</ul><div className="pagination"><button className="button secondary" disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 20))}>Anterior</button><span>{data.total ? `${offset + 1}–${Math.min(offset + data.items.length, data.total)}` : 'Sin eventos'}</span><button className="button secondary" disabled={offset + 20 >= data.total} onClick={() => setOffset(offset + 20)}>Siguiente</button></div></>}
  </section>
}
