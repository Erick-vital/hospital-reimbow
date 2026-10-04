import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, get, isAbort } from '../api/client'
import type { Field, Identity, PatientContext, PatientPage } from '../api/contracts'
import type { Session } from '../identity/session'
import { Heading } from '../components/Heading'
import { has, patientName } from './ReadViews'
import { absent, AgeField, Collection, DraftSummary, normalizeDraft, TextField } from './FormFields'
import { CreationFeedback, RecoveryNotice, useCreation } from './useCreation'

type Identifier = { system: string; value: string }
type Evidence = { field: string; source_kind: string; source_reference: string }
type Profile = NonNullable<PatientContext['administrative_profile']>
type Description = NonNullable<PatientContext['unidentified_description']>
type DescriptionDraft = Omit<Description, 'estimated_age'> & { estimated_age: Field<{ min_years: number | null; max_years: number | null }> }
const normalize = (value: string) => value.trim().normalize('NFC')
const addressLabels = { street: 'Calle', exterior: 'Número exterior', interior: 'Número interior', neighborhood: 'Colonia', postal_code: 'Código postal', municipality: 'Municipio', state: 'Estado', country: 'País', references: 'Referencias' }

export function PatientRegistration({ session, identity }: { session: Session; identity: Identity }) {
  const [unknown, setUnknown] = useState(false)
  const [names, setNames] = useState({ given_names: absent<string>(), family_name: absent<string>(), second_family_name: absent<string>(), birth_date: absent<string>() })
  const [identifiers, setIdentifiers] = useState<Identifier[]>([])
  const [profile, setProfile] = useState<Profile>({ registered_sex: absent(), nationality: absent(), phones: absent(), addresses: absent(), emergency_contacts: absent() })
  const [description, setDescription] = useState<DescriptionDraft>({ apparent_sex: absent(), estimated_age: absent(), identifying_features: absent(), origin: absent(), transferred_by: absent() })
  const [verified, setVerified] = useState(false)
  const [evidence, setEvidence] = useState<Evidence[]>([])
  const [search, setSearch] = useState<{ page: PatientPage; time: number; query: string } | null>(null)
  const [searchError, setSearchError] = useState<ApiError | null>(null)
  const [searching, setSearching] = useState(false)
  const [reviewed, setReviewed] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const [validation, setValidation] = useState('')
  const searchRun = useRef(0)
  const creation = useCreation<PatientContext>(session, '/api/v2/patients')
  useEffect(() => {
    if (creation.error && !creation.locked) setConfirm(false)
    if (creation.error?.code === 'SEARCH_REQUIRED') { setSearch(null); setReviewed(false) }
  }, [creation.error, creation.locked])
  function invalidateIdentity() {
    searchRun.current++; setSearching(false); setSearch(null); setSearchError(null); setReviewed(false)
    setVerified(false); setEvidence([]); setConfirm(false)
  }
  const fullName = [names.given_names.value, names.family_name.value, names.second_family_name.value].filter(Boolean).map(value => normalize(value!)).join(' ')
  async function find(offset = 0) {
    const context = session.context()
    const run = ++searchRun.current
    const filters = new URLSearchParams({ limit: '20', offset: String(offset) })
    if (identifiers.length) {
      filters.set('identifier_system', identifiers[0].system); filters.set('identifier_value', identifiers[0].value.trim().toUpperCase())
    } else if (fullName) filters.set('name', fullName)
    else filters.set('unidentified', 'true')
    setSearching(true); setSearch(null); setSearchError(null); setReviewed(false); setConfirm(false)
    try {
      const page = await get<PatientPage>(`/api/v2/patients?${filters}`, context)
      if (run === searchRun.current && context.isCurrent(context.generation)) setSearch({ page, time: Date.now(), query: filters.toString() })
    } catch (failure) {
      if (run === searchRun.current && context.isCurrent(context.generation) && !isAbort(failure)) setSearchError(failure instanceof ApiError ? failure : new ApiError(0, 'NETWORK_ERROR'))
    } finally { if (run === searchRun.current && context.isCurrent(context.generation)) setSearching(false) }
  }
  function body() {
    return normalizeDraft({ search_id: search?.page.search_id, is_unidentified: unknown, identity_status: verified ? 'verified' : 'provisional',
      ...Object.fromEntries(Object.entries(names).map(([key, field]) => [key, field.value === null ? null : normalize(field.value)])),
      identity_field_states: Object.fromEntries(Object.entries(names).map(([key, field]) => [key, field.state])),
      identifiers, administrative_profile: profile, unidentified_description: description, verification: verified ? evidence : [] })
  }
  function review(event: React.FormEvent) {
    event.preventDefault(); setValidation('')
    const normalizedIdentifiers = identifiers.map(item => ({ system: item.system, value: item.value.trim().toUpperCase() }))
    if (identifiers.some(item => !/^[\x00-\x7F]*$/.test(item.value) || !(item.system === 'CURP' ? /^[A-Z0-9]{18}$/ : /^[A-Z0-9_-]{1,64}$/).test(item.value.trim().toUpperCase())) || new Set(normalizedIdentifiers.map(item => item.system + ':' + item.value)).size !== identifiers.length) { setValidation('Revisa el formato de identificadores: CURP de 18 caracteres, TEST de 1–64 caracteres ASCII, sin duplicados.'); return }
    if (names.birth_date.value && names.birth_date.value > new Date().toLocaleDateString('en-CA')) { setValidation('El nacimiento no puede ser futuro.'); return }
    if (profile.addresses.value?.some(item => !Object.entries(item).some(([key, value]) => key !== 'kind' && typeof value === 'string' && normalize(value)))) { setValidation('Captura al menos un componente de cada domicilio o quita la fila.'); return }
    if ([...(profile.phones.value ?? []).map(item => item.number), ...(profile.emergency_contacts.value ?? []).map(item => item.name), ...identifiers.map(item => item.value), ...evidence.map(item => item.source_reference)].some(value => !normalize(value))) { setValidation('Completa las filas y referencias con un valor válido o quítalas.'); return }
    if (description.estimated_age.value && (description.estimated_age.value.min_years === null || description.estimated_age.value.max_years === null || description.estimated_age.value.min_years > description.estimated_age.value.max_years)) { setValidation('Completa un rango de edad estimada válido: mínimo no mayor que máximo.'); return }
    if (!search || !reviewed || Date.now() - search.time >= 15 * 60 * 1000) {
      setValidation('Busca de nuevo y revisa las coincidencias. El borrador se conserva.'); return
    }
    if (verified && (!evidence.some(e => e.field === 'full_name') || !evidence.some(e => ['birth_date', 'CURP'].includes(e.field)))) {
      setValidation('Contrasta el nombre y nacimiento o CURP con sus fuentes.'); return
    }
    setConfirm(true)
  }
  if (creation.result) return <section className="card"><Heading>Paciente registrado</Heading><p role="status">{patientName(creation.result)} · {creation.result.folio}</p>
    {has(identity, 'patients.read') && <Link to={`/patients/${creation.result.id}`}>Consultar paciente y abrir episodio</Link>}
    <p>UUID: {creation.result.id}</p></section>
  const blocked = creation.locked || confirm
  return <section className="card"><Heading>Registrar paciente</Heading><p className="lead">Borrador en memoria. Busca coincidencias con estos datos antes de registrar. Al salir o cambiar actor se descarta.</p>
    <RecoveryNotice />
    <div className="draft-banner" aria-label="Paciente por registrar">{unknown ? 'Identidad desconocida' : fullName || 'Identidad no informada'} · {verified ? 'Verificación por documentar' : 'Provisional'} · Folio pendiente del servidor</div>
    <form onSubmit={review}>
      <fieldset disabled={blocked}><legend>Identidad y perfil administrativo</legend>
        <label>Tipo de identidad<select value={unknown ? 'unknown' : 'partial'} onChange={e => {
          const nextUnknown = e.target.value === 'unknown'
          const discard = nextUnknown ? Object.values(names).some(field => field.value !== null || field.state !== 'not_provided') || identifiers.length > 0 || verified : Object.values(description).some(field => field.value !== null || field.state !== 'not_provided')
          if (discard && !window.confirm(nextUnknown ? 'Se descartarán identidad, identificadores y verificación. ¿Continuar?' : 'Se descartarán los descriptores del desconocido. ¿Continuar?')) return
          invalidateIdentity(); setUnknown(nextUnknown)
          setNames({ given_names: absent(), family_name: absent(), second_family_name: absent(), birth_date: absent() }); setIdentifiers([])
          setDescription({ apparent_sex: absent(), estimated_age: absent(), identifying_features: absent(), origin: absent(), transferred_by: absent() })
        }}><option value="partial">Identidad total o parcialmente conocida</option><option value="unknown">Identidad completamente desconocida</option></select></label>
        {!unknown && <><div className="form-grid">{Object.entries({ given_names: 'Nombres', family_name: 'Primer apellido', second_family_name: 'Segundo apellido', birth_date: 'Fecha de nacimiento' }).map(([key, label]) => <TextField key={key} label={label} allowNA={key === 'second_family_name'} type={key === 'birth_date' ? 'date' : 'text'} max={100} field={names[key as keyof typeof names]} change={field => { invalidateIdentity(); setNames({ ...names, [key]: field }) }} />)}</div>
          <h3>Identificadores</h3>{identifiers.map((item, index) => <fieldset key={index}><legend>Identificador {index + 1}</legend><label>Sistema<select aria-label="Sistema" value={item.system} onChange={e => { invalidateIdentity(); setIdentifiers(identifiers.map((v, i) => i === index ? { ...v, system: e.target.value } : v)) }}><option>CURP</option><option>TEST</option></select></label>
            <label>Valor<input required maxLength={64} value={item.value} onChange={e => { invalidateIdentity(); setIdentifiers(identifiers.map((v, i) => i === index ? { ...v, value: e.target.value } : v)) }} /></label><button type="button" className="button secondary" onClick={() => { invalidateIdentity(); setIdentifiers(identifiers.filter((_, i) => i !== index)) }}>Quitar identificador {index + 1}</button></fieldset>)}
          <button type="button" className="button secondary" disabled={identifiers.length >= 10} onClick={() => { invalidateIdentity(); setIdentifiers([...identifiers, { system: 'CURP', value: '' }]) }}>Añadir identificador</button></>}
        <div className="form-grid"><TextField label="Sexo registrado" max={100} field={profile.registered_sex} change={field => setProfile({ ...profile, registered_sex: field })} /><TextField label="Nacionalidad" max={100} field={profile.nationality} change={field => setProfile({ ...profile, nationality: field })} /></div>
        <Collection label="Teléfonos" field={profile.phones} change={field => setProfile({ ...profile, phones: field })} empty={() => ({ kind: 'personal', number: '' })}>{(item, change) => <div className="form-grid"><label>Tipo de teléfono<select value={item.kind} onChange={e => change({ ...item, kind: e.target.value })}>{['personal', 'fixed', 'work', 'other'].map((key, i) => <option key={key} value={key}>{['Personal', 'Fijo', 'Laboral', 'Otro'][i]}</option>)}</select></label><label>Número de teléfono<input required maxLength={40} value={item.number} onChange={e => change({ ...item, number: e.target.value })} /></label></div>}</Collection>
        <Collection label="Domicilios" field={profile.addresses} change={field => setProfile({ ...profile, addresses: field })} empty={() => ({ kind: 'principal', street: null, exterior: null, interior: null, neighborhood: null, postal_code: null, municipality: null, state: null, country: null, references: null })}>{(item, change) => <><label>Tipo de domicilio<select value={item.kind} onChange={e => change({ ...item, kind: e.target.value })}>{['principal', 'temporary', 'fiscal', 'correspondence', 'other'].map((key, i) => <option key={key} value={key}>{['Principal', 'Temporal', 'Fiscal', 'Correspondencia', 'Otro'][i]}</option>)}</select></label><div className="form-grid">{Object.entries(addressLabels).map(([key, label]) => <label key={key}>{label}<input maxLength={key === 'references' ? 500 : key === 'postal_code' ? 20 : 200} value={item[key as keyof typeof addressLabels] ?? ''} onChange={e => change({ ...item, [key]: normalize(e.target.value) ? e.target.value : null })} /></label>)}</div><p>Captura al menos un componente del domicilio.</p></>}</Collection>
        <Collection label="Contactos de emergencia" field={profile.emergency_contacts} change={field => setProfile({ ...profile, emergency_contacts: field })} empty={() => ({ name: '', relationship: absent<string>(), phone: absent<string>() })}>{(item, change) => <><label>Nombre del contacto<input required maxLength={200} value={item.name} onChange={e => change({ ...item, name: e.target.value })} /></label><div className="form-grid"><TextField allowNA label="Relación del contacto" max={100} field={item.relationship} change={field => change({ ...item, relationship: field })} /><TextField allowNA label="Teléfono del contacto" max={40} field={item.phone} change={field => change({ ...item, phone: field })} /></div></>}</Collection>
        {unknown && <fieldset><legend>Caracterización del desconocido</legend><p>Descriptores opcionales, separados de identidad y nacimiento.</p><div className="form-grid">{Object.entries({ apparent_sex: 'Sexo aparente', identifying_features: 'Características de identificación', origin: 'Procedencia al registro', transferred_by: 'Traslado al registro' }).map(([key, label]) => <TextField key={key} label={label} max={key === 'identifying_features' ? 1000 : key === 'apparent_sex' ? 100 : 200} field={description[key as Exclude<keyof Description, 'estimated_age'>]} change={field => setDescription({ ...description, [key]: field })} />)}</div>
          <AgeField field={description.estimated_age} change={field => setDescription({ ...description, estimated_age: field })} /></fieldset>}
        {!unknown && has(identity, 'patients.verify_identity') && <fieldset><legend>Verificación declarada</legend><label>Estado de identidad<select value={verified ? 'verified' : 'provisional'} onChange={e => { setVerified(e.target.value === 'verified'); setEvidence([]) }}><option value="provisional">Provisional</option><option value="verified">Verificada con evidencia</option></select></label>
          {verified && <><p>Contrasta nombre más nacimiento o CURP. No incluir números completos de documentos ni adjuntos.</p>{['full_name', ...(names.birth_date.state === 'known' ? ['birth_date'] : []), ...(identifiers.some(i => i.system === 'CURP') ? ['CURP'] : [])].map(field => {
            const item = evidence.find(e => e.field === field)
            return <fieldset key={field}><legend>{({ full_name: 'Nombre contrastado', birth_date: 'Nacimiento contrastado', CURP: 'CURP contrastada' })[field]}</legend><label>Contraste<select aria-label="Contraste" value={item ? 'yes' : 'no'} onChange={e => setEvidence(e.target.value === 'yes' ? [...evidence, { field, source_kind: 'official_document', source_reference: '' }] : evidence.filter(v => v.field !== field))}><option value="no">Pendiente</option><option value="yes">Contrastado</option></select></label>
              {item && <><label>Fuente<select value={item.source_kind} onChange={e => setEvidence(evidence.map(v => v.field === field ? { ...v, source_kind: e.target.value } : v))}><option value="official_document">Documento oficial</option><option value="institutional_document">Documento institucional</option></select></label><label>Referencia descriptiva<input required maxLength={200} value={item.source_reference} onChange={e => setEvidence(evidence.map(v => v.field === field ? { ...v, source_reference: e.target.value } : v))} /></label></>}</fieldset>
          })}</>}
        </fieldset>}
      </fieldset>
      <fieldset disabled={blocked}><legend>Búsqueda previa y coincidencias</legend><p>Se busca el primer identificador informado, el nombre completo o registros desconocidos si no hay identidad. Las coincidencias requieren revisión, sin fusión automática.</p>
        <button type="button" className="button secondary" disabled={searching} onClick={() => void find()}>Buscar coincidencias del borrador</button>
        {searching && <p role="status">Buscando coincidencias…</p>}{searchError && <p role="alert">{searchError.message} {searchError.requestId}</p>}
        {search && <><p>{search.page.total} coincidencias. Búsqueda válida durante 15 minutos.</p><ul className="record-list">{search.page.items.map(item => <li key={item.id}>{patientName(item)} · {item.folio}{has(identity, 'patients.read') && <Link to={`/patients/${item.id}`}>Seleccionar paciente existente {item.folio}</Link>}</li>)}</ul>
          <div className="pagination"><button className="button secondary" type="button" disabled={!search.page.offset} onClick={() => void find(Math.max(0, search.page.offset - 20))}>Coincidencias anteriores</button><button className="button secondary" type="button" disabled={search.page.offset + 20 >= search.page.total} onClick={() => void find(search.page.offset + 20)}>Más coincidencias</button></div>
          <label className="check"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />Revisé las coincidencias y corresponde registrar una persona nueva</label></>}
      </fieldset>
      {validation && <p role="alert">{validation}</p>}
      {!confirm && !creation.locked && <button className="button" type="submit">Revisar registro</button>}
      {confirm && !creation.locked && <div className="confirmation"><h3>Confirmar registro de paciente</h3><p>{unknown ? 'Identidad desconocida' : fullName || 'Identidad no informada'} · {verified ? 'Verificada con evidencia declarada' : 'Provisional'}. Revisa el resumen antes de confirmar.</p><DraftSummary values={{ ...names, ...profile, ...(unknown ? description : {}), identifiers, ...(verified ? { verification: evidence } : {}) }} /><button className="button" type="button" autoFocus onClick={() => void creation.send(body())}>Confirmar registro</button><button className="button secondary" type="button" onClick={() => setConfirm(false)}>Volver al borrador</button></div>}
    </form><CreationFeedback creation={creation} />
  </section>
}
