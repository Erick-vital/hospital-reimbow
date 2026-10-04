import { useState } from 'react'
import { Link, useParams } from 'react-router'
import type { Field, Identity, PageResult, PatientContext } from '../api/contracts'
import { ApiError } from '../api/client'
import { ErrorNotice, Loading } from '../components/Feedback'
import { Heading } from '../components/Heading'
import { useResource } from '../components/useResource'
import type { Session } from '../identity/session'
import { admissionTypes, has, patientName } from '../patients/ReadViews'

interface Catalog { id: string; code: string; name: string; site_id?: string }
interface Episode {
  id: string; folio: string; patient_id: string; type: keyof typeof admissionTypes; status: 'open'; created_at: string
  admitted_at: Field<string>; site: Field<Catalog>; service: Field<Catalog>
}
interface Attention { patient: PatientContext; episode: Episode }
interface Longitudinal { patient: PatientContext; attentions?: PageResult<{ episode: Episode }> }
const api = '/api/v3/clinical'
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const absence = { known: 'Conocido', unknown: 'Desconocido', not_provided: 'No proporcionado', not_applicable: 'No aplica' }
const quality = { pending: 'Identidad provisional', documented: 'Verificación documentada', legacy_unsubstantiated: 'Declaración anterior sin evidencia' }
const date = (value: string) => new Date(value).toLocaleString('es-MX', { timeZoneName: 'longOffset' })
const catalog = (field: Field<Catalog>) => field.value?.name ?? absence[field.state]

function Pagination({ data, change }: { data: PageResult<unknown>; change: (offset: number) => void }) {
  return <nav className="pagination" aria-label="Paginación de atenciones">
    <button className="button secondary" disabled={!data.offset} onClick={() => change(Math.max(0, data.offset - data.limit))}>Anterior</button>
    <span role="status">{data.items.length ? `${data.offset + 1}–${data.offset + data.items.length} de ${data.total}` : `0 en esta página · ${data.total} atenciones`}</span>
    <button className="button secondary" disabled={data.offset + data.limit >= data.total} onClick={() => change(data.offset + data.limit)}>Siguiente</button>
  </nav>
}
function EpisodeDetails({ episode }: { episode: Episode }) {
  return <dl className="details">
    <div><dt>Tipo / estado</dt><dd>{admissionTypes[episode.type]} · Abierto</dd></div>
    <div><dt>Ingreso efectivo</dt><dd>{episode.admitted_at.value ? date(episode.admitted_at.value) : absence[episode.admitted_at.state]}</dd></div>
    <div><dt>Fecha de registro</dt><dd>{date(episode.created_at)}</dd></div>
    <div><dt>Sede</dt><dd>{catalog(episode.site)}</dd></div>
    <div><dt>Servicio</dt><dd>{catalog(episode.service)}</dd></div>
  </dl>
}
function ClinicalBanner({ patient, episode }: { patient: PatientContext; episode?: Episode }) {
  return <section className="patient-banner clinical-banner" aria-label="Contexto clínico actual">
    <div><div className="section-label">Paciente · {patient.folio}</div><strong>{patientName(patient)}</strong><p>{quality[patient.verification_quality]}</p></div>
    <div><strong>{episode ? episode.folio : 'Vista longitudinal'}</strong><p>{episode ? `${admissionTypes[episode.type]} · Abierto` : 'Sin episodio seleccionado'}</p></div>
  </section>
}
function NoClinicalSections() {
  return <p className="empty-message">Esta etapa permite consultar la identificación y las atenciones. Las mediciones, alergias y notas todavía no están disponibles.</p>
}

export function AttentionList({ session, identity }: { session: Session; identity: Identity }) {
  const [type, setType] = useState('')
  const [site, setSite] = useState('')
  const [service, setService] = useState('')
  const [limit, setLimit] = useState(20)
  const [offset, setOffset] = useState(0)
  const [sitesOffset, setSitesOffset] = useState(0)
  const [servicesOffset, setServicesOffset] = useState(0)
  const [notice, setNotice] = useState('')
  const canCatalog = has(identity, 'clinical.catalogs.read')
  const sites = useResource<PageResult<Catalog>>(session, canCatalog ? `${api}/catalogs/sites?limit=100&offset=${sitesOffset}` : null)
  const services = useResource<PageResult<Catalog>>(session, canCatalog && site ? `${api}/catalogs/services?site_id=${site}&limit=100&offset=${servicesOffset}` : null)
  const filters = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  if (type) filters.set('type', type)
  if (site) filters.set('site_id', site)
  if (service) filters.set('service_id', service)
  const { data, error } = useResource<PageResult<Attention>>(session, `${api}/attentions?${filters}`)
  return <section className="card"><div className="section-label">Consulta clínica · acceso demo global</div><Heading>Atenciones abiertas</Heading>
    <p className="lead">Selecciona una atención por paciente y folio de episodio.</p>
    <div className="search-form">
      <label>Tipo de atención<select value={type} onChange={e => { setType(e.target.value); setOffset(0) }}><option value="">Todos</option>{Object.entries(admissionTypes).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      {canCatalog && <>
        <label>Sede<select value={site} onChange={e => { setSite(e.target.value); setService(''); setServicesOffset(0); setOffset(0); setNotice('El filtro de servicio se limpió al cambiar sede.') }}><option value="">Todas</option>{sites.data?.items.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        {sites.data && sites.data.total > 100 && <Pagination data={sites.data} change={value => { setSitesOffset(value); setSite(''); setService(''); setOffset(0) }} />}
        <label>Servicio<select disabled={!site || !services.data} value={service} onChange={e => { setService(e.target.value); setOffset(0) }}><option value="">Todos</option>{services.data?.items.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        {services.data && services.data.total > 100 && <Pagination data={services.data} change={value => { setServicesOffset(value); setService(''); setOffset(0) }} />}
      </>}
      <label>Atenciones por página<select value={limit} onChange={e => { setLimit(Number(e.target.value)); setOffset(0) }}><option>5</option><option>20</option><option>50</option><option>100</option></select></label>
    </div>
    {notice && <p role="status">{notice}</p>}
    {!canCatalog && <p>Filtros de sede y servicio: acceso no disponible.</p>}
    {(sites.error || services.error) && <ErrorNotice error={(sites.error || services.error)!} retry={session.refresh} />}
    {error ? <ErrorNotice error={error} retry={session.refresh} /> : !data ? <Loading message="Consultando atenciones…" /> : <>
      {!data.items.length && <p className="empty-message">Sin atenciones abiertas en esta página para estos filtros.</p>}
      <ul className="record-list" aria-label="Atenciones abiertas">{data.items.map(({ patient, episode }) => <li key={episode.id}>
        <div><strong>{patientName(patient)}</strong><p>{patient.folio} · {episode.folio}</p><p>{quality[patient.verification_quality]}</p><p>{admissionTypes[episode.type]} · {catalog(episode.site)} · {catalog(episode.service)}</p></div>
        <Link to={`/clinical/attentions/${episode.id}`}>Abrir atención {episode.folio}</Link>
      </li>)}</ul><Pagination data={data} change={setOffset} />
    </>}
  </section>
}

export function ClinicalContext({ session, longitudinal = false }: { session: Session; longitudinal?: boolean }) {
  const { episodeId, patientId } = useParams()
  const id = longitudinal ? patientId : episodeId
  const valid = !!id && uuid.test(id)
  const [offset, setOffset] = useState(0)
  const path = valid ? (longitudinal ? `${api}/patients/${id}/context?limit=20&offset=${offset}` : `${api}/attentions/${id}/context`) : null
  const { data, error } = useResource<Attention | Longitudinal>(session, path)
  if (!valid) return <ErrorNotice error={new ApiError(404, 'RESOURCE_NOT_FOUND')} />
  if (error) return <ErrorNotice error={error} retry={session.refresh} />
  if (!data) return <Loading message="Resolviendo contexto clínico…" />
  const episode = 'episode' in data ? data.episode : undefined
  return <><ClinicalBanner patient={data.patient} episode={episode} />
    <section className="card"><Heading>{longitudinal ? 'Atenciones del paciente' : 'Contexto de la atención'}</Heading>
      <p><Link to="/clinical/attentions">Volver a atenciones abiertas</Link></p>
      {episode && <><EpisodeDetails episode={episode} /><p><Link to={`/clinical/patients/${data.patient.id}`}>Consultar vista longitudinal {data.patient.folio}</Link></p><NoClinicalSections /></>}
      {'attentions' in data && data.attentions && <>
        <p>Información agrupada por episodio; esta página muestra {data.attentions.items.length} de {data.attentions.total} atenciones.</p>
        {!data.attentions.items.length && <p className="empty-message">Sin atenciones en esta página.</p>}
        <ul className="record-list" aria-label="Atenciones del paciente">{data.attentions.items.map(({ episode: item }) => <li key={item.id}><div><strong>{item.folio}</strong><EpisodeDetails episode={item} /></div><Link to={`/clinical/attentions/${item.id}`}>Abrir atención {item.folio}</Link></li>)}</ul>
        <Pagination data={data.attentions} change={setOffset} /><NoClinicalSections />
      </>}
      {longitudinal && !('attentions' in data) && <p>Lista de atenciones: acceso no disponible.</p>}
    </section>
  </>
}
