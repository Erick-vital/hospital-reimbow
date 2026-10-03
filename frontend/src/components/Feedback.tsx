import { Heading } from './Heading'
import { ApiError } from '../api/client'

export function Loading({ message = 'Comprobando acceso…' }: { message?: string }) {
  return <div className="feedback" role="status" aria-live="polite"><span className="spinner" aria-hidden="true" />{message}</div>
}

export function ErrorNotice({ error, retry }: { error: ApiError; retry?: () => void }) {
  const title = error.status === 401 || error.status === 403 ? 'Acceso no disponible'
    : error.status === 404 ? 'Registro no encontrado' : 'Consulta no disponible'
  return <section className="card error-card" role="alert">
    <div className="section-label">Revisa el acceso</div>
    <Heading>{title}</Heading>
    <p>{error.message}</p>
    {error.requestId && <p className="correlation">Referencia de la solicitud: <code>{error.requestId}</code></p>}
    {retry && <button type="button" className="button" onClick={retry}>Revalidar acceso</button>}
  </section>
}
