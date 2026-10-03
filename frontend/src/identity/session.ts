import { ApiError, DEMO_ENABLED, get, isAbort, staleRequest } from '../api/client'
import type { RequestContext } from '../api/client'
import type { Identity } from '../api/contracts'

type Phase = 'idle' | 'loading' | 'ready' | 'denied' | 'error'
export interface SessionSnapshot {
  generation: number
  actorKey: string | null
  path: string
  phase: Phase
  identity: Identity | null
  error: ApiError | null
}

// Una sola generación cancela y descarta peticiones de actor/ruta/borrador previos.
// Ninguna identidad, respuesta o intención se guarda fuera de memoria.
export class Session {
  private controllers = new Set<AbortController>()
  private listeners = new Set<() => void>()
  private value: SessionSnapshot = {
    generation: 0, actorKey: DEMO_ENABLED ? 'admision-demo' : null,
    path: window.location.pathname, phase: 'idle', identity: null, error: null,
  }

  snapshot = () => this.value
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener) } }
  private publish(value: SessionSnapshot) { this.value = value; this.listeners.forEach(listener => listener()) }
  private clear(phase: Phase, error: ApiError | null = null) {
    this.controllers.forEach(controller => controller.abort())
    this.controllers.clear()
    this.publish({ ...this.value, generation: this.value.generation + 1, identity: null, phase, error })
  }

  context(): RequestContext {
    const { generation, actorKey } = this.value
    return {
      actorKey, generation,
      isCurrent: captured => captured === this.value.generation,
      register: controller => {
        if (generation !== this.value.generation) { controller.abort(); staleRequest() }
        this.controllers.add(controller)
        return () => { this.controllers.delete(controller) }
      },
      onAccessDenied: error => {
        this.clear('denied', error)
        // Revalidar permisos sin volver a ejecutar automáticamente la ruta denegada.
        void this.verify(error)
      },
    }
  }

  enterPath(path: string) {
    if (path !== this.value.path || this.value.phase === 'idle') {
      this.value = { ...this.value, path }
      this.refresh()
    }
  }
  changeActor(actorKey: string) {
    if (!DEMO_ENABLED || actorKey === this.value.actorKey) return
    this.value = { ...this.value, actorKey }
    this.refresh()
  }
  refresh = () => { this.clear('loading'); void this.verify() }
  pause = () => this.clear('idle')

  private async verify(blocked: ApiError | null = null) {
    const context = this.context()
    try {
      const identity = await get<Identity>('/api/v1/identity/me', context, { identity: true })
      if (!context.isCurrent(context.generation)) return
      this.publish({ ...this.value, identity, phase: blocked ? 'denied' : 'ready', error: blocked })
    } catch (error) {
      if (isAbort(error) || !context.isCurrent(context.generation)) return
      const failure = error instanceof ApiError ? error : new ApiError(0, 'NETWORK_ERROR')
      this.publish({ ...this.value, identity: null, error: failure,
        phase: failure.status === 401 || failure.status === 403 ? 'denied' : 'error' })
    }
  }
}
