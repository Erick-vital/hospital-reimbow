import { lazy, Suspense, useEffect, useLayoutEffect, useState, useSyncExternalStore } from 'react'
import { BrowserRouter, Link, NavLink, Navigate, Route, Routes, useLocation, useParams } from 'react-router'
import { ApiError } from './api/client'
import type { AdmissionContext, Identity, PatientContext } from './api/contracts'
import { ErrorNotice, Loading } from './components/Feedback'
import { Heading } from './components/Heading'
import { useResource } from './components/useResource'
import { Session } from './identity/session'
import { AdmissionDetails, EpisodeList, PatientBanner, PatientDetails, PatientSearch, has } from './patients/ReadViews'
import type { SessionSnapshot } from './identity/session'
import { PatientRegistration } from './patients/PatientRegistration'
import { AdmissionRegistration } from './patients/AdmissionRegistration'
import { AuditView } from './patients/AuditView'

const DemoSelector = import.meta.env.DEV && import.meta.env.VITE_DEMO_IDENTITY === 'true' ? lazy(() => import('./identity/DemoSelector')) : null
const uuid = /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i

function PatientArea({ session, identity, createAdmission = false }: { session: Session; identity: Identity; createAdmission?: boolean }) {
  const { patientId } = useParams()
  const validId = patientId && uuid.test(patientId)
  const { data, error } = useResource<PatientContext>(session, validId ? `/api/v2/patients/${patientId}` : null)
  if (!validId) return <ErrorNotice error={new ApiError(404, 'RESOURCE_NOT_FOUND')} />
  if (error) return <ErrorNotice error={error} retry={session.refresh} />
  if (!data) return <Loading message="Resolviendo el paciente…" />
  return <><PatientBanner patient={data} />{createAdmission ? <AdmissionRegistration key={data.id} session={session} identity={identity} patient={data} /> : <>
    <PatientDetails patient={data} identity={identity} />
    {has(identity, 'admissions.create') && <p><Link className="button" to={`/patients/${data.id}/admissions/new`}>Abrir nueva atención</Link></p>}
    {has(identity, 'admissions.read') ? <EpisodeList session={session} patientId={data.id} /> : <p>No tienes permiso para consultar los episodios.</p>}
  </>}</>
}

function AdmissionArea({ session, identity }: { session: Session; identity: Identity }) {
  const { admissionId } = useParams()
  const validId = admissionId && uuid.test(admissionId)
  const { data, error } = useResource<AdmissionContext>(session, validId ? `/api/v2/admissions/${admissionId}` : null)
  if (!validId) return <ErrorNotice error={new ApiError(404, 'RESOURCE_NOT_FOUND')} />
  if (error) return <ErrorNotice error={error} retry={session.refresh} />
  if (!data) return <Loading message="Resolviendo el episodio…" />
  return <ResolvedAdmission session={session} admission={data} identity={identity} />
}

function ResolvedAdmission({ session, admission, identity }: { session: Session; admission: AdmissionContext; identity: Identity }) {
  const canReadPatient = has(identity, 'patients.read')
  const { data, error } = useResource<PatientContext>(session, canReadPatient ? `/api/v2/patients/${admission.patient_id}` : null)
  if (error) return <ErrorNotice error={error} retry={session.refresh} />
  if (canReadPatient && !data) return <Loading message="Resolviendo el paciente del episodio…" />
  return <>{data && <PatientBanner patient={data} />}
    <section className="card"><div className="section-label">Episodio de atención</div>
      <Heading>{admission.folio}</Heading>
      <p className="lead">{({ emergency: 'Urgencias', outpatient: 'Consulta externa', inpatient: 'Hospitalización' })[admission.type]} · Abierto</p>
      <AdmissionDetails admission={admission} identity={identity} />
      {!canReadPatient && <p>No tienes permiso para consultar la identificación del paciente.</p>}
      {data && <Link className="text-link" to={`/patients/${data.id}`}>Volver al paciente</Link>}
    </section>
  </>
}

function Gate({ identity, permissions, children }: { identity: Identity; permissions: string[]; children: React.ReactNode }) {
  return has(identity, ...permissions) ? children : <ErrorNotice error={new ApiError(403, 'PERMISSION_DENIED')} />
}

function Areas({ session, identity }: { session: Session; identity: Identity }) {
  return <Routes>
    <Route path="/" element={<Navigate to="/patients" replace />} />
    <Route path="/patients" element={<Gate identity={identity} permissions={['patients.search']}><PatientSearch session={session} identity={identity} /></Gate>} />
    <Route path="/patients/new" element={<Gate identity={identity} permissions={['patients.create', 'patients.search']}><PatientRegistration session={session} identity={identity} /></Gate>} />
    <Route path="/patients/:patientId" element={<Gate identity={identity} permissions={['patients.read']}><PatientArea session={session} identity={identity} /></Gate>} />
    <Route path="/patients/:patientId/admissions/new" element={<Gate identity={identity} permissions={['patients.read', 'admissions.create']}><PatientArea session={session} identity={identity} createAdmission /></Gate>} />
    <Route path="/admissions/:admissionId" element={<Gate identity={identity} permissions={['admissions.read']}><AdmissionArea session={session} identity={identity} /></Gate>} />
    <Route path="/audit" element={<Gate identity={identity} permissions={['audit.read']}><AuditView session={session} /></Gate>} />
    <Route path="*" element={<ErrorNotice error={new ApiError(404, 'RESOURCE_NOT_FOUND')} />} />
  </Routes>
}

function Workspace({ session, state }: { session: Session; state: SessionSnapshot }) {
  const location = useLocation()
  useLayoutEffect(() => { session.enterPath(location.pathname) }, [session, location.pathname])
  useEffect(() => {
    const show = (event: PageTransitionEvent) => { if (event.persisted) session.refresh() }
    window.addEventListener('pageshow', show)
    window.addEventListener('pagehide', session.pause)
    return () => { window.removeEventListener('pageshow', show); window.removeEventListener('pagehide', session.pause) }
  }, [session])
  // La ruta y generación forman el límite de vida de datos/borradores locales.
  const ready = state.path === location.pathname && state.phase === 'ready' && state.identity !== null
  useEffect(() => {
    const heading = document.querySelector<HTMLElement>('[data-page-heading]')
    heading?.focus()
  }, [location.pathname, state.generation, state.phase])
  return <div className="app-shell">
    <a className="skip-link" href="#main">Ir al contenido</a>
    <aside className="sidebar">
      <Link to="/patients" className="brand" aria-label="Reimbow HIS, inicio"><span className="brand-mark" aria-hidden="true">+</span><span>reimbow<small>HOSPITAL INFORMATION SYSTEM</small></span></Link>
      <div className="sidebar-section">ESPACIO DE TRABAJO</div>
      <nav aria-label="Navegación principal">
        {has(state.identity, 'patients.search') && <NavLink to="/patients" end><span aria-hidden="true">○</span> Pacientes</NavLink>}
        {has(state.identity, 'audit.read') && <NavLink to="/audit"><span aria-hidden="true">≡</span> Auditoría</NavLink>}
      </nav>
      <div className="sidebar-note"><span className="status-dot" aria-hidden="true" />Entorno local<small>Datos ficticios · Demostración</small></div>
    </aside>
    <div className="workspace">
      <header className="topbar"><div><span className="section-label">Reimbow HIS</span><h1>Pacientes y Admisión</h1></div>
        <div className="connection"><span className={`status-dot ${state.phase !== 'ready' ? 'pending' : ''}`} aria-hidden="true" />
          {state.phase === 'ready' ? 'Acceso comprobado' : 'Validación de acceso'}</div>
      </header>
      {DemoSelector && <div className="demo-strip"><div><strong>Demostración local</strong><span>El actor elegido no autentica a una persona.</span></div>
        <Suspense fallback={<Loading message="Cargando selector…" />}><DemoSelector actorKey={state.actorKey} onChange={actor => session.changeActor(actor)} /></Suspense>
      </div>}
      <main id="main" tabIndex={-1}>
        <div className="breadcrumb">ESPACIO DE TRABAJO <span>/</span> PACIENTES Y ADMISIÓN</div>
        {state.path !== location.pathname || state.phase === 'loading' || state.phase === 'idle' ? <Loading />
          : ready && state.identity ? <Areas key={`${state.generation}:${location.pathname}`} session={session} identity={state.identity} />
            : <ErrorNotice error={state.error ?? new ApiError(401, 'IDENTITY_REQUIRED')} retry={session.refresh} />}
        {state.phase === 'ready' && state.identity && <section className="access-summary" aria-label="Acceso actual">
          <div><span className="section-label">Acceso consultado en el servidor</span><p>Actor: <strong>{state.identity.actor_key}</strong></p></div>
          <button type="button" className="button secondary" onClick={session.refresh}>Revalidar acceso</button>
        </section>}
      </main>
      <footer>Reimbow HIS <span>Uso local con datos ficticios</span></footer>
    </div>
  </div>
}

export default function App() {
  const [session] = useState(() => new Session())
  const state = useSyncExternalStore(session.subscribe, session.snapshot)
  return <BrowserRouter><Workspace session={session} state={state} /></BrowserRouter>
}
