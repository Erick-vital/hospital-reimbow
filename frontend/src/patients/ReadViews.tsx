import { useState } from 'react'
import { Link } from 'react-router'
import type { AdmissionContext, Field, FieldState, Identity, PageResult, PatientContext, PatientPage } from '../api/contracts'
import { ErrorNotice, Loading } from '../components/Feedback'
import { Heading } from '../components/Heading'
import { useResource } from '../components/useResource'
import type { Session } from '../identity/session'

export const has = (identity: Identity | null, ...permissions: string[]) => permissions.every(p => identity?.permissions.includes(p))
export const patientName = (patient: PatientContext) => [patient.given_names, patient.family_name, patient.second_family_name].filter(Boolean).join(' ') || (patient.is_unidentified ? 'Identidad desconocida' : 'Identidad no informada')
const states: Record<FieldState, string> = { known: 'Conocido', unknown: 'Desconocido', not_provided: 'No proporcionado', not_applicable: 'No aplica' }
const quality = { pending: 'Identidad provisional', documented: 'Verificación documentada', legacy_unsubstantiated: 'Declaración anterior sin evidencia' }
const kinds: Record<string, string> = { personal: 'Personal', fixed: 'Fijo', work: 'Laboral', other: 'Otro', principal: 'Principal', temporary: 'Temporal', fiscal: 'Fiscal', correspondence: 'Correspondencia' }
export const admissionTypes = { emergency: 'Urgencias', outpatient: 'Consulta externa', inpatient: 'Hospitalización' }
const dateTime = (value: string) => new Date(value).toLocaleString('es-MX', { timeZoneName: 'short' })
const fieldText = (field: Field<string>) => field.state === 'known' ? field.value : states[field.state]
function Detail({ label, children }: { label: string; children: React.ReactNode }) { return <div><dt>{label}</dt><dd>{children}</dd></div> }

export function PatientBanner({ patient }: { patient: PatientContext }) {
  const name = patientName(patient)
  return <section className="patient-banner" aria-label="Paciente del contexto actual">
    <span className="avatar" aria-hidden="true">{patient.given_names?.slice(0, 1) || '?'}</span>
    <div><div className="section-label">Paciente</div><strong>{name}</strong><div className="folio">{patient.folio}</div></div>
    <span className="tag">{quality[patient.verification_quality]}</span>
  </section>
}

function Pagination({ page, onChange }: { page: PageResult<unknown>; onChange: (offset: number) => void }) {
  return <nav className="pagination" aria-label="Paginación">
    <button className="button secondary" disabled={page.offset === 0} onClick={() => onChange(Math.max(0, page.offset - page.limit))}>Anterior</button>
    <span role="status">{page.total ? `${page.offset + 1}–${Math.min(page.offset + page.items.length, page.total)} de ${page.total}` : '0 resultados'}</span>
    <button className="button secondary" disabled={page.offset + page.limit >= page.total} onClick={() => onChange(page.offset + page.limit)}>Siguiente</button>
  </nav>
}

export function PatientSearch({ session, identity }: { session: Session; identity: Identity }) {
  const [query, setQuery] = useState<URLSearchParams | null>(null)
  const [offset, setOffset] = useState(0)
  const [requestKey, setRequestKey] = useState(0)
  const [mode, setMode] = useState('identity')
  const [validation, setValidation] = useState('')
  const path = query ? `/api/v2/patients?${query.toString()}&offset=${offset}` : null
  const { data, error } = useResource<PatientPage>(session, path, requestKey)
  function search(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const filters = new URLSearchParams({ limit: String(form.get('limit')) })
    if (mode === 'unidentified') filters.set('unidentified', 'true')
    else {
      for (const field of ['folio', 'name', 'identifier_value']) {
        const value = String(form.get(field) || '').trim()
        if (value) filters.set(field, value)
      }
      if (filters.has('identifier_value')) filters.set('identifier_system', String(form.get('identifier_system')))
      if (![...filters.keys()].some(key => key !== 'limit')) { setValidation('Indica al menos un filtro para buscar.'); return }
    }
    setValidation(''); setOffset(0); setQuery(filters); setRequestKey(key => key + 1)
  }
  return <section className="card">
    <div className="section-label">Identificación de pacientes</div><Heading>Pacientes</Heading>
    <p className="lead">Busca y revisa las coincidencias antes de seleccionar. Un nombre parecido no confirma la identidad.</p>
    {has(identity, 'patients.create') && <Link className="button secondary" to="/patients/new">Registrar paciente nuevo</Link>}
    <form onSubmit={search} className="search-form">
      <label>Tipo de búsqueda<select value={mode} onChange={event => { setMode(event.target.value); setQuery(null); setValidation('') }}><option value="identity">Datos de identidad</option><option value="unidentified">Identidad desconocida registrada en V2</option></select></label>
      {mode === 'identity' && <>
        <label>Folio de paciente<input name="folio" maxLength={32} placeholder="PAC-…" /></label>
        <label>Nombre<input name="name" maxLength={302} /></label>
        <label>Sistema de identificador<select name="identifier_system"><option>CURP</option><option>TEST</option></select></label>
        <label>Valor del identificador<input name="identifier_value" maxLength={64} /></label>
      </>}
      <label>Resultados por página<select name="limit" defaultValue="20"><option>5</option><option>20</option><option>50</option><option>100</option></select></label>
      <button className="button" type="submit">Buscar</button>
    </form>
    {validation && <p role="alert">{validation}</p>}
    {!query && <p className="empty-message">Indica filtros y pulsa Buscar.</p>}
    {query && error && <ErrorNotice error={error} retry={session.refresh} />}
    {query && !error && !data && <Loading message="Buscando coincidencias…" />}
    {data && <div className="search-results" aria-label="Coincidencias">
      <p>{data.total ? 'Candidatos encontrados. Revisa su folio e identificación.' : 'Sin coincidencias para estos filtros.'}</p>
      <ul className="record-list">{data.items.map(patient => <li key={patient.id}>
        <div><strong>{patientName(patient)}</strong><p>{patient.folio} · {quality[patient.verification_quality]}</p>
          {has(identity, 'patients.read_demographics') && patient.birth_date && <p>Nacimiento: {patient.birth_date}</p>}</div>
        {has(identity, 'patients.read') && <Link to={`/patients/${patient.id}`}>Consultar paciente {patient.folio}</Link>}
      </li>)}</ul>
      <Pagination page={data} onChange={setOffset} />
    </div>}
  </section>
}

export function PatientDetails({ patient, identity }: { patient: PatientContext; identity: Identity }) {
  const profile = has(identity, 'patients.read_demographics') ? patient.administrative_profile : undefined
  const description = patient.unidentified_description
  return <section className="card">
    <div className="section-label">Información administrativa</div><Heading>Ficha de paciente</Heading>
    <p className="lead">Esta ficha identifica al paciente. Cada episodio representa una atención distinta.</p>
    <dl className="details"><Detail label="Calidad de verificación">{quality[patient.verification_quality]}</Detail>
      <Detail label="Estado de identidad">{patient.identity_status === 'verified' ? 'Declarada verificada' : 'Provisional'}</Detail></dl>
    {profile ? <>
      <dl className="details">
        <Detail label="Nombres">{patient.given_names || states[patient.identity_field_states?.given_names || 'not_provided']}</Detail>
        <Detail label="Primer apellido">{patient.family_name || states[patient.identity_field_states?.family_name || 'not_provided']}</Detail>
        <Detail label="Segundo apellido">{patient.second_family_name || states[patient.identity_field_states?.second_family_name || 'not_provided']}</Detail>
        <Detail label="Fecha de nacimiento">{patient.birth_date || states[patient.identity_field_states?.birth_date || 'not_provided']}</Detail>
        <Detail label="Sexo registrado">{fieldText(profile.registered_sex)}</Detail><Detail label="Nacionalidad">{fieldText(profile.nationality)}</Detail>
        <Detail label="Identificadores">{patient.identifiers?.length ? patient.identifiers.map((item, index) => <p key={index}>{item.system}: {item.value}</p>) : 'No proporcionados'}</Detail>
        <Detail label="Fecha de registro">{patient.created_at && dateTime(patient.created_at)}</Detail>
      </dl>
      {patient.administrative_origin === 'legacy' && <p>Registro anterior: la información ampliada no fue capturada.</p>}
      <h3>Teléfonos</h3>{profile.phones.state !== 'known' ? <p>{states[profile.phones.state]}</p> : <ul>{profile.phones.value?.map((phone, index) => <li key={index}>{kinds[phone.kind]}: {phone.number}</li>)}{!profile.phones.value?.length && <li>Sin teléfonos registrados</li>}</ul>}
      <h3>Domicilios</h3>{profile.addresses.state !== 'known' ? <p>{states[profile.addresses.state]}</p> : <ul>{profile.addresses.value?.map((address, index) => <li key={index}>
        <strong>{kinds[address.kind]}</strong><dl className="details">{Object.entries({ Calle: address.street, Exterior: address.exterior, Interior: address.interior, Colonia: address.neighborhood, 'Código postal': address.postal_code, Municipio: address.municipality, Estado: address.state, País: address.country, Referencias: address.references }).map(([label, value]) => <Detail key={label} label={label}>{value || 'No proporcionado'}</Detail>)}</dl>
      </li>)}{!profile.addresses.value?.length && <li>Sin domicilios registrados</li>}</ul>}
      <h3>Contactos de emergencia</h3>{profile.emergency_contacts.state !== 'known' ? <p>{states[profile.emergency_contacts.state]}</p> : <ul>{profile.emergency_contacts.value?.map((contact, index) => <li key={index}><strong>{contact.name}</strong><p>Relación: {fieldText(contact.relationship)} · Teléfono: {fieldText(contact.phone)}</p></li>)}{!profile.emergency_contacts.value?.length && <li>Sin contactos registrados</li>}</ul>}
      {patient.is_unidentified && description && <><h3>Caracterización de identidad desconocida</h3><dl className="details">
        <Detail label="Sexo aparente">{fieldText(description.apparent_sex)}</Detail>
        <Detail label="Edad estimada">{description.estimated_age.state === 'known' && description.estimated_age.value ? `${description.estimated_age.value.min_years}–${description.estimated_age.value.max_years} años (estimación)` : states[description.estimated_age.state]}</Detail>
        <Detail label="Características">{fieldText(description.identifying_features)}</Detail><Detail label="Procedencia del desconocido">{fieldText(description.origin)}</Detail><Detail label="Trasladado por">{fieldText(description.transferred_by)}</Detail>
      </dl></>}
    </> : <p>No tienes permiso para consultar la demografía ampliada.</p>}
    <p className="scope-note">El expediente clínico longitudinal no está disponible en esta versión.</p>
  </section>
}

export function EpisodeList({ session, patientId }: { session: Session; patientId: string }) {
  const [offset, setOffset] = useState(0)
  const [limit, setLimit] = useState(20)
  const { data, error } = useResource<PageResult<AdmissionContext>>(session, `/api/v2/patients/${patientId}/admissions?limit=${limit}&offset=${offset}`)
  return <section className="card"><h3>Episodios del paciente</h3>
    <label>Atenciones por página<select value={limit} onChange={event => { setLimit(Number(event.target.value)); setOffset(0) }}><option>5</option><option>20</option><option>50</option></select></label>
    {error ? <ErrorNotice error={error} retry={session.refresh} /> : !data ? <Loading message="Consultando episodios…" /> : <>
      {!data.items.length && <p>Sin episodios en esta página.</p>}
      <ul className="record-list">{data.items.map(admission => <li key={admission.id}><div><strong>{admission.folio}</strong><p>{admissionTypes[admission.type]} · Abierto</p><p>Registro: {dateTime(admission.created_at)}</p></div><Link to={`/admissions/${admission.id}`}>Consultar episodio {admission.folio}</Link></li>)}</ul>
      <Pagination page={data} onChange={setOffset} />
    </>}
  </section>
}

export function AdmissionDetails({ admission, identity }: { admission: AdmissionContext; identity: Identity }) {
  const intake = has(identity, 'admissions.read_intake') ? admission.intake : undefined
  return <>
    <dl className="details"><Detail label="Registro del episodio">{dateTime(admission.created_at)}</Detail></dl>
    {intake ? <><h3>Datos de ingreso</h3><dl className="details">
      <Detail label="Fecha clínica de ingreso">{intake.admitted_at.state === 'known' && intake.admitted_at.value ? dateTime(intake.admitted_at.value) : states[intake.admitted_at.state]}</Detail>
      <Detail label="Sede (identificador)">{fieldText(intake.site_id)}</Detail><Detail label="Servicio (identificador)">{fieldText(intake.service_id)}</Detail>
      <Detail label="Procedencia del ingreso">{fieldText(intake.origin)}</Detail><Detail label="Motivo referido">{fieldText(intake.reason_for_visit)}</Detail>
    </dl>{admission.intake_origin === 'legacy' && <p>Registro anterior: los datos de ingreso ampliados no fueron capturados.</p>}</> : <p>No tienes permiso para consultar los datos de ingreso.</p>}
  </>
}
