import { useEffect, useState } from 'react'
import { ApiError, get, isAbort } from '../api/client'
import type { Session } from '../identity/session'

export function useResource<T>(session: Session, path: string | null) {
  const [result, setResult] = useState<{ data: T | null; error: ApiError | null }>({ data: null, error: null })
  useEffect(() => {
    if (!path) return
    const context = session.context()
    const controller = new AbortController()
    setResult({ data: null, error: null })
    void get<T>(path, context, { signal: controller.signal }).then(data => {
      if (context.isCurrent(context.generation) && !controller.signal.aborted) setResult({ data, error: null })
    }).catch((error: unknown) => {
      if (!isAbort(error) && context.isCurrent(context.generation) && !controller.signal.aborted) {
        setResult({ data: null, error: error instanceof ApiError ? error : new ApiError(0, 'NETWORK_ERROR') })
      }
    })
    return () => controller.abort()
  }, [session, path])
  return result
}
