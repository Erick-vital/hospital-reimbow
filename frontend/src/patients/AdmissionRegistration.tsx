import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, get, isAbort } from '../api/client'
import type { AdmissionContext, Identity, PageResult, PatientContext } from '../api/contracts'
import type { Session } from '../identity/session'
import { Heading } from '../components/Heading'
import { absent, DraftSummary, normalizeDraft, TextField } from './FormFields'
import { admissionTypes, has, patientName } from './ReadViews'
import { CreationFeedback, RecoveryNotice, useCreation } from './useCreation'

interface CatalogItem { id: string; name: string }
// Catálogos paginados completos; selección de sede invalida servicio y respuestas anteriores.
async function catalog(path: string, session: Session, signal: AbortSignal) {
  const items: CatalogItem[] = []
  const context = session.context()
  for (let offset = 0; ; offset += 100) {
    const page = await get<PageResult<CatalogItem>>(`${path}${path.includes('?') ? '&' : '?'}limit=100&offset=${offset}`, context, { signal })
    items.push(...page.items)
    if (offset + 100 >= page.total) return items
  }
}
export function AdmissionRegistration({ session, identity, patient }: { session: Session; identity: Identity; patient: PatientContext }) {
  const [type, setType] = useState<AdmissionContext['type']>('emergency')
  const [intake, setIntake] = useState<NonNullable<AdmissionContext['intake']>>({ admitted_at: absent(), site_id: absent(), service_id: absent(), origin: absent(), reason_for_visit: absent() })
  const [sites, setSites] = useState<CatalogItem[]>([])
  const [services, setServices] = useState<{ site: string; items: CatalogItem[] } | null>(null)
  const [catalogError, setCatalogError] = useState<ApiError | null>(null)
  const [retry, setRetry] = useState(0)
  const [confirm, setConfirm] = useState(false)
  const [validation, setValidation] = useState('')
  const creation = useCreation<AdmissionContext>(session, '/api/v2/admissions')
  const site = intake.site_id.value ?? ''
  useEffect(() => {
    const controller = new AbortController()
    setCatalogError(null)
    void catalog('/api/v2/catalogs/sites', session, controller.signal).then(setSites).catch(error => {
      if (!isAbort(error)) setCatalogError(error instanceof ApiError ? error : new ApiError(0, 'NETWORK_ERROR'))
    })
    return () => controller.abort()
  }, [session, retry])
  useEffect(() => {
    const controller = new AbortController()
    setServices(null); setCatalogError(null)
    if (site) void catalog(`/api/v2/catalogs/services?site_id=${site}`, session, controller.signal).then(items => setServices({ site, items })).catch(error => {
      if (!isAbort(error)) setCatalogError(error instanceof ApiError ? error : new ApiError(0, 'NETWORK_ERROR'))
    })
    return () => controller.abort()
  }, [session, site, retry])
  useEffect(() => { if (creation.error && !creation.locked) setConfirm(false) }, [creation.error, creation.locked])
  function review(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setValidation('')
    if (type !== 'emergency' && ['admitted_at', 'site_id', 'service_id'].some(key => intake[key as keyof typeof intake].state !== 'known')) {
      setValidation('Consulta externa y hospitalización requieren fecha de ingreso, sede y servicio conocidos.'); return
    }
    if (intake.service_id.state === 'known' && (!site || !services?.items.some(item => item.id === intake.service_id.value))) {
      setValidation('Selecciona un servicio vigente de la sede.'); return
    }
    if (intake.admitted_at.value && new Date(intake.admitted_at.value).getTime() > Date.now()) { setValidation('La fecha clínica de ingreso no puede ser futura.'); return }
    if (!event.currentTarget.reportValidity()) return
    setConfirm(true)
  }
  function body() {
    return normalizeDraft({ patient_id: patient.id, type, intake: { ...intake,
      admitted_at: intake.admitted_at.value ? { state: 'known', value: new Date(intake.admitted_at.value).toISOString() } : intake.admitted_at } })
  }
  if (creation.result) return <section className="card"><Heading>Episodio abierto</Heading><p role="status">{creation.result.folio} · {admissionTypes[creation.result.type]}</p><p>Paciente: {patientName(patient)} · {patient.folio}</p>
    {has(identity, 'admissions.read') && <Link to={`/admissions/${creation.result.id}`}>Consultar episodio {creation.result.folio}</Link>}
    <p><Link to={`/patients/${patient.id}`}>Volver al paciente para abrir otra atención</Link></p></section>
  const pending = Object.values(intake).some(field => field.state !== 'known')
  return <section className="card"><Heading>Abrir episodio</Heading><p className="lead">Cada confirmación abre una atención para el paciente identificado arriba. Fecha clínica distinta del registro; captura sólo datos conocidos.</p>
    <RecoveryNotice patientId={patient.id} />
    <form noValidate onSubmit={review}><fieldset disabled={creation.locked || confirm}><legend>Tipo y datos de ingreso</legend>
      <label>Tipo de atención<select value={type} onChange={e => setType(e.target.value as AdmissionContext['type'])}>{Object.entries(admissionTypes).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      {type === 'emergency' && pending && <p role="status">Datos de ingreso pendientes. Urgencias permite continuar conservando las razones de ausencia.</p>}
      {type !== 'emergency' && <p>Fecha de ingreso, sede y servicio deben ser conocidos.</p>}
      <p>La fecha/hora se captura en la zona local: {Intl.DateTimeFormat().resolvedOptions().timeZone}.</p>
      <div className="form-grid"><TextField label="Fecha clínica de ingreso" required={type !== 'emergency'} type="datetime-local" field={intake.admitted_at} change={field => setIntake({ ...intake, admitted_at: field })} />
        <TextField required={type !== 'emergency'} label="Sede" field={intake.site_id} options={sites} change={field => { setIntake({ ...intake, site_id: field, service_id: absent() }); setValidation('Al cambiar sede se descarta el servicio anterior. Selecciona el servicio de esta sede si corresponde.') }} />
        <TextField required={type !== 'emergency'} label="Servicio" field={intake.service_id} options={services?.site === site ? services.items : []} change={field => setIntake({ ...intake, service_id: field })} />
        <TextField label="Procedencia del ingreso" field={intake.origin} change={field => setIntake({ ...intake, origin: field })} />
        <TextField label="Motivo referido de atención" max={1000} field={intake.reason_for_visit} change={field => setIntake({ ...intake, reason_for_visit: field })} /></div>
      <button type="button" className="button secondary" onClick={() => { const now = new Date(); now.setMinutes(now.getMinutes() - now.getTimezoneOffset()); setIntake({ ...intake, admitted_at: { state: 'known', value: now.toISOString().slice(0, 16) } }) }}>Usar hora actual</button>
      {intake.admitted_at.value && <p>Hora capturada: {new Date(intake.admitted_at.value).toString()}</p>}
      {has(identity, 'patients.read_demographics') && patient.is_unidentified && patient.unidentified_description?.origin.state === 'known' && <button className="button secondary" type="button" onClick={() => setIntake({ ...intake, origin: { ...patient.unidentified_description!.origin } })}>Copiar procedencia del registro del paciente</button>}
    </fieldset>
    {catalogError && <div role="alert"><p>{catalogError.message} {catalogError.requestId}</p><button className="button secondary" type="button" onClick={() => setRetry(value => value + 1)}>Recargar catálogos</button></div>}
    {validation && <p role="alert">{validation}</p>}
    {!confirm && !creation.locked && <button className="button" type="submit">Revisar apertura</button>}
    {confirm && !creation.locked && <div className="confirmation"><h3>Confirmar paciente y atención</h3><p>{patientName(patient)} · {patient.folio} · {admissionTypes[type]}</p><p>{pending ? 'Datos de ingreso pendientes según los campos capturados.' : 'Datos de ingreso conocidos.'} Revisa el resumen del ingreso.</p><DraftSummary values={{ ...intake, site_id: intake.site_id.state === 'known' ? { ...intake.site_id, value: sites.find(item => item.id === site)?.name ?? site } : intake.site_id, service_id: intake.service_id.state === 'known' ? { ...intake.service_id, value: services?.items.find(item => item.id === intake.service_id.value)?.name ?? intake.service_id.value } : intake.service_id }} /><button className="button" type="button" autoFocus onClick={() => void creation.send(body())}>Confirmar apertura</button><button className="button secondary" type="button" onClick={() => setConfirm(false)}>Volver al borrador</button></div>}
    </form><CreationFeedback creation={creation} />
  </section>
}
