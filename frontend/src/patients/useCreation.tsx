import { useRef, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, get, isAbort } from '../api/client'
import type { Session } from '../identity/session'

// El cuerpo y la clave viven juntos sólo en memoria. El ref bloquea incluso dos
// clics antes del siguiente render; cualquier resultado incierto los conserva.
export function useCreation<T>(session: Session, path: string) {
  const intent = useRef<{ key: string; body: string; started: number } | null>(null)
  const busy = useRef(false)
  const [pending, setPending] = useState(false)
  const [locked, setLocked] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [result, setResult] = useState<T | null>(null)
  const [reconcile, setReconcile] = useState(false)
  async function send(body?: unknown) {
    if (busy.current || result || reconcile) return
    if (!intent.current) {
      if (body === undefined) return
      intent.current = { key: crypto.randomUUID(), body: JSON.stringify(body), started: Date.now() }
    }
    if (Date.now() - intent.current.started >= 24 * 60 * 60 * 1000) {
      setError(new ApiError(409, 'IDEMPOTENCY_EXPIRED')); setReconcile(true); return
    }
    busy.current = true; setPending(true); setLocked(true); setError(null)
    const context = session.context()
    try {
      const value = await get<T>(path, context, { body: intent.current.body, key: intent.current.key })
      if (context.isCurrent(context.generation)) setResult(value)
    } catch (failure) {
      if (isAbort(failure) || !context.isCurrent(context.generation)) return
      const problem = failure instanceof ApiError ? failure : new ApiError(0, 'NETWORK_ERROR')
      setError(problem)
      if (['IDEMPOTENCY_CONFLICT', 'IDEMPOTENCY_EXPIRED'].includes(problem.code)) setReconcile(true)
      // Estas respuestas confirman rechazo sin creación; permiten corregir.
      else if (problem.status === 422 || problem.code === 'IDENTIFIER_CONFLICT' || problem.status === 404) {
        intent.current = null; setLocked(false)
      }
    } finally {
      busy.current = false
      if (context.isCurrent(context.generation)) setPending(false)
    }
  }
  return { send, pending, locked, error, result, reconcile }
}

export function CreationFeedback({ creation }: { creation: ReturnType<typeof useCreation> }) {
  return <>{creation.error && <div role="alert" className="creation-error"><p>{creation.error.message}</p>
    <p>Código: {creation.error.code}</p>{creation.error.requestId && <p>Referencia de la solicitud: {creation.error.requestId}</p>}</div>}
    {creation.locked && !creation.result && <p role="status">El resultado puede estar pendiente. Los datos del intento permanecen congelados. Al salir, cambiar actor o recargar se pierde el intento: consulta los registros antes de otra alta.</p>}
    {creation.pending && <p role="status">Enviando alta…</p>}
    {creation.locked && !creation.pending && !creation.result && !creation.reconcile && <button type="button" className="button" onClick={() => void creation.send()}>Reintentar el mismo intento</button>}
    {creation.reconcile && <Link to="/patients">Consultar y reconciliar registros</Link>}
  </>
}

// Aviso independiente de la intención: sigue disponible después de recargar,
// aunque el borrador se haya perdido, sin persistir datos o claves del paciente.
export function RecoveryNotice({ patientId }: { patientId?: string }) {
  return <aside className="confirmation" aria-label="Recuperación de un alta anterior">
    <p>Si una confirmación anterior quedó sin respuesta, consulta los registros antes de iniciar otra alta. Salir, cambiar actor o recargar descarta el intento y no cancela un alta que el servidor ya recibió.</p>
    <Link to={patientId ? `/patients/${patientId}` : '/patients'}>{patientId ? 'Consultar las atenciones del paciente' : 'Buscar un paciente ya registrado'}</Link>
    {!patientId && <p>Si era una persona desconocida y no recuperaste su folio, solicita revisión al supervisor antes de repetir el registro.</p>}
  </aside>
}
