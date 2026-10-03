import type { Field, FieldState } from '../api/contracts'

export const absent = <T,>(): Field<T> => ({ state: 'not_provided', value: null })
export const states: Record<FieldState, string> = { known: 'Conocido', unknown: 'Desconocido', not_provided: 'No proporcionado', not_applicable: 'No aplica' }

export function StateSelect({ label, value, change }: { label: string; value: FieldState; change: (state: FieldState) => void }) {
  return <label>{label}<select aria-label={label} value={value} onChange={e => change(e.target.value as FieldState)}>{Object.entries(states).map(([key, text]) => <option key={key} value={key}>{text}</option>)}</select></label>
}

export function TextField({ label, field, change, type = 'text', max = 200, options }: { label: string; field: Field<string>; change: (field: Field<string>) => void; type?: string; max?: number; options?: { id: string; name: string }[] }) {
  return <div className="field-pair"><StateSelect label={`${label}: disponibilidad`} value={field.state} change={state => change({ state, value: state === 'known' ? '' : null })} />
    {field.state === 'known' && <label>{label}{options ? <select aria-label={label} required value={field.value ?? ''} onChange={e => change({ state: 'known', value: e.target.value })}><option value="">Selecciona…</option>{options.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select>
      : <input required type={type} maxLength={max} value={field.value ?? ''} onChange={e => change({ state: 'known', value: e.target.value })} />}</label>}
  </div>
}

export function Collection<T>({ label, field, change, empty, children }: { label: string; field: Field<T[]>; change: (field: Field<T[]>) => void; empty: () => T; children: (item: T, change: (item: T) => void, index: number) => React.ReactNode }) {
  const items = field.value ?? []
  return <fieldset><legend>{label}</legend><StateSelect label={`${label}: disponibilidad`} value={field.state} change={state => change({ state, value: state === 'known' ? [] : null })} />
    {field.state === 'known' && <>{items.map((item, index) => <fieldset key={index}><legend>{label} {index + 1}</legend>{children(item, updated => change({ state: 'known', value: items.map((old, i) => i === index ? updated : old) }), index)}
      <button type="button" className="button secondary" onClick={() => change({ state: 'known', value: items.filter((_, i) => i !== index) })}>Quitar {label.toLowerCase()} {index + 1}</button></fieldset>)}
      <button type="button" className="button secondary" disabled={items.length >= 10} onClick={() => change({ state: 'known', value: [...items, empty()] })}>Añadir {label.toLowerCase()}</button><p>Máximo 10. Una lista conocida vacía indica que no hay elementos.</p></>}
  </fieldset>
}
