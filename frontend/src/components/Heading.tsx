import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'

export function Heading({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLHeadingElement>(null)
  useEffect(() => { ref.current?.focus() }, [])
  return <h2 ref={ref} tabIndex={-1} data-page-heading>{children}</h2>
}
