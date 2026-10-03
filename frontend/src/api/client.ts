export const DEMO_ENABLED = import.meta.env.DEV && import.meta.env.VITE_DEMO_IDENTITY === 'true'

const messages: Record<string, string> = {
  IDENTITY_REQUIRED: 'La identidad no está disponible. Revisa el actor o la habilitación del modo local.',
  PERMISSION_DENIED: 'El actor actual no tiene permiso para esta acción.',
  RESOURCE_NOT_FOUND: 'El registro solicitado no se encontró.',
  VALIDATION_ERROR: 'Revisa los datos de la solicitud.',
  DATABASE_UNAVAILABLE: 'No fue posible consultar el servidor. Intenta nuevamente.',
  INTERNAL_ERROR: 'No fue posible completar la consulta. Intenta nuevamente.',
  NETWORK_ERROR: 'No fue posible conectar con el servidor. Intenta nuevamente.',
  TIMEOUT: 'La consulta tardó demasiado. Intenta nuevamente.',
  INVALID_RESPONSE: 'El servidor devolvió una respuesta no válida.',
}

export class ApiError extends Error {
  constructor(readonly status: number, readonly code: string, readonly requestId?: string) {
    super(messages[code] ?? 'No fue posible completar la consulta.')
    this.name = 'ApiError'
  }
}

export function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

export function staleRequest(): never {
  throw new DOMException('Contexto cancelado', 'AbortError')
}

export interface RequestContext {
  actorKey: string | null
  generation: number
  isCurrent: (generation: number) => boolean
  register: (controller: AbortController) => () => void
  onAccessDenied: (error: ApiError) => void
}

export async function get<T>(path: string, context: RequestContext, options: { signal?: AbortSignal; identity?: boolean } = {}): Promise<T> {
  if (!path.startsWith('/api/')) throw new Error('Ruta API relativa requerida')
  const controller = new AbortController()
  const unregister = context.register(controller)
  const abort = () => controller.abort()
  options.signal?.addEventListener('abort', abort, { once: true })
  if (options.signal?.aborted) abort()
  let timedOut = false
  const timer = setTimeout(() => { timedOut = true; controller.abort() }, 10_000)
  const current = () => {
    if (!context.isCurrent(context.generation) || options.signal?.aborted) staleRequest()
  }
  try {
    const headers: Record<string, string> = { Accept: 'application/json' }
    if (DEMO_ENABLED && context.actorKey) headers['X-Dev-Actor'] = context.actorKey
    const response = await fetch(path, { headers, signal: controller.signal, cache: 'no-store', credentials: 'omit' })
    current()
    const rawId = response.headers.get('X-Request-ID')
    const requestId = rawId && /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(rawId) ? rawId : undefined
    let body: unknown
    try { body = await response.json() } catch { current(); throw new ApiError(response.status, 'INVALID_RESPONSE', requestId) }
    current()
    if (!response.ok) {
      const code = typeof body === 'object' && body !== null && 'error' in body
        && typeof body.error === 'object' && body.error !== null && 'code' in body.error && typeof body.error.code === 'string'
        ? body.error.code : 'INTERNAL_ERROR'
      const error = new ApiError(response.status, code, requestId)
      if (!options.identity && (response.status === 401 || response.status === 403)) context.onAccessDenied(error)
      throw error
    }
    return body as T
  } catch (error) {
    current()
    if (error instanceof ApiError) throw error
    if (timedOut) throw new ApiError(0, 'TIMEOUT')
    if (isAbort(error)) throw error
    throw new ApiError(0, 'NETWORK_ERROR')
  } finally {
    clearTimeout(timer)
    unregister()
    options.signal?.removeEventListener('abort', abort)
  }
}
