import { useRef } from 'react'
import type { Field, FieldState } from '../api/contracts'

export const absent = <T,>(): Field<T> => ({ state: 'not_provided', value: null })
export const states: Record<FieldState, string> = { known: 'Conocido', unknown: 'Desconocido', not_provided: 'No proporcionado', not_applicable: 'No aplica' }
export const normalize = (value: string) => value.trim().normalize('NFC')

export function AbsenceSelect({ label, value, change, allowNA = false }: { label: string; value: FieldState; change: (state: FieldState) => void; allowNA?: boolean }) {
  const options: FieldState[] = ['not_provided', 'unknown', ...(allowNA ? ['not_applicable' as const] : [])]
  // Conservar razones históricas aunque no se ofrezcan para captura nueva.
  if (value !== 'known' && !options.includes(value)) options.push(value)
  return <label>{label}<select aria-label={label} value={value} onChange={e => change(e.target.value as FieldState)}>{options.map(key => <option key={key} value={key}>{states[key]}</option>)}</select></label>
}

export function TextField({ label, field, change, type = 'text', max = 200, options, allowNA = false, required = false }: { label: string; field: Field<string>; change: (field: Field<string>) => void; type?: string; max?: number; options?: { id: string; name: string }[]; allowNA?: boolean; required?: boolean }) {
  const reason = useRef<FieldState>('not_provided')
  if (field.state !== 'known') reason.current = field.state
  const empty = !normalize(field.value ?? '')
  function update(value: string) { change(normalize(value) ? { state: 'known', value } : { state: reason.current, value: null }) }
  return <div className="field-pair"><label>{label}{options ? <select aria-label={label} required={required} value={field.value ?? ''} onChange={e => update(e.target.value)}><option value="">Selecciona…</option>{options.map(item => <option value={item.id} key={item.id}>{item.name}</option>)}</select>
    : <input type={type} required={required} maxLength={max} max={type === 'date' ? new Date().toLocaleDateString('en-CA') : undefined} value={field.value ?? ''} onChange={e => update(e.target.value)} />}</label>
    {empty && !required && <AbsenceSelect label={`${label}: razón de ausencia`} value={field.state === 'known' ? reason.current : field.state} allowNA={allowNA} change={state => { reason.current = state; change({ state, value: null }) }} />}
  </div>
}

export function Collection<T>({ label, field, change, empty, children }: { label: string; field: Field<T[]>; change: (field: Field<T[]>) => void; empty: () => T; children: (item: T, change: (item: T) => void, index: number) => React.ReactNode }) {
  const reason = useRef<FieldState>('not_provided')
  if (field.state !== 'known') reason.current = field.state
  const items = field.value ?? []
  // Cada fila conserva sus razones al retirar otra fila, sin reutilizar su componente.
  const rowKeys = useRef<string[]>([])
  rowKeys.current = rowKeys.current.slice(0, items.length)
  while (rowKeys.current.length < items.length) rowKeys.current.push(crypto.randomUUID())
  return <fieldset><legend>{label}</legend>
    {!items.length && (field.state === 'known' ? <p role="status">Ninguno declarado</p> : <AbsenceSelect label={`${label}: razón de ausencia`} value={field.state} change={state => change({ state, value: null })} />)}
    {items.map((item, index) => <fieldset key={rowKeys.current[index]}><legend>{label} {index + 1}</legend>{children(item, updated => change({ state: 'known', value: items.map((old, i) => i === index ? updated : old) }), index)}
      <button type="button" className="button secondary" onClick={() => { rowKeys.current.splice(index, 1); const remaining = items.filter((_, i) => i !== index); change(remaining.length ? { state: 'known', value: remaining } : { state: reason.current, value: null }) }}>Quitar {label.toLowerCase()} {index + 1}</button></fieldset>)}
    <button type="button" className="button secondary" disabled={items.length >= 10} onClick={() => change({ state: 'known', value: [...items, empty()] })}>Añadir {label.toLowerCase()}</button>
    {!items.length && <button type="button" className="button secondary" onClick={() => change(field.state === 'known' ? { state: reason.current, value: null } : { state: 'known', value: [] })}>{field.state === 'known' ? 'Retirar declaración' : 'Ninguno declarado'}: {label.toLowerCase()}</button>}
    <p>Máximo 10. Revisa cada fila antes de confirmar.</p>
  </fieldset>
}

export function AgeField({ field, change }: { field: Field<{ min_years: number | null; max_years: number | null }>; change: (field: Field<{ min_years: number | null; max_years: number | null }>) => void }) {
  const reason = useRef<FieldState>('not_provided')
  if (field.state !== 'known') reason.current = field.state
  return <fieldset><legend>Edad estimada</legend><div className="form-grid">{(['min_years', 'max_years'] as const).map((key, i) => <label key={key}>{i ? 'Edad máxima estimada' : 'Edad mínima estimada'}<input type="number" required={field.state === 'known'} min={0} max={150} step={1} value={field.value?.[key] ?? ''} onChange={e => {
    const value = { min_years: null, max_years: null, ...field.value, [key]: e.target.value === '' ? null : Number(e.target.value) }
    change(value.min_years === null && value.max_years === null ? { state: reason.current, value: null } : { state: 'known', value })
  }} /></label>)}</div>{field.state !== 'known' && <AbsenceSelect label="Edad estimada: razón de ausencia" value={field.state} change={state => change({ state, value: null })} />}</fieldset>
}

// Normalizar el cuerpo sin cambiar los estados de ausencia, incluida la lista known/[] explícita.
export function normalizeDraft<T>(value: T): T {
  if (typeof value === 'string') return normalize(value) as T
  if (Array.isArray(value)) return value.map(normalizeDraft) as T
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, normalizeDraft(item)])) as T
  return value
}

const labels: Record<string, string> = { identifiers: 'Identificadores', verification: 'Evidencia de verificación', full_name: 'Nombre contrastado', personal: 'Personal', fixed: 'Fijo', work: 'Laboral', other: 'Otro', principal: 'Principal', temporary: 'Temporal', fiscal: 'Fiscal', correspondence: 'Correspondencia', given_names: 'Nombres', family_name: 'Primer apellido', second_family_name: 'Segundo apellido', birth_date: 'Fecha de nacimiento', registered_sex: 'Sexo registrado', nationality: 'Nacionalidad', phones: 'Teléfonos', addresses: 'Domicilios', emergency_contacts: 'Contactos de emergencia', apparent_sex: 'Sexo aparente', estimated_age: 'Edad estimada', identifying_features: 'Características de identificación', origin: 'Procedencia', transferred_by: 'Traslado al registro', admitted_at: 'Fecha clínica de ingreso', site_id: 'Sede', service_id: 'Servicio', reason_for_visit: 'Motivo referido de atención', kind: 'Tipo', number: 'Número', name: 'Nombre del contacto', relationship: 'Relación del contacto', phone: 'Teléfono del contacto', min_years: 'Edad mínima', max_years: 'Edad máxima', street: 'Calle', exterior: 'Número exterior', interior: 'Número interior', neighborhood: 'Colonia', postal_code: 'Código postal', municipality: 'Municipio', state: 'Estado', country: 'País', references: 'Referencias', system: 'Sistema', value: 'Valor', field: 'Campo contrastado', source_kind: 'Fuente', source_reference: 'Referencia descriptiva', official_document: 'Documento oficial', institutional_document: 'Documento institucional' }
function display(value: unknown): React.ReactNode {
  if (value === null || value === undefined || value === '') return 'Sin dato'
  if (Array.isArray(value)) return value.length ? <ol>{value.map((item, i) => <li key={i}>{display(item)}</li>)}</ol> : 'Ninguno declarado'
  if (typeof value === 'object') {
    const item = value as Record<string, unknown>
    if ('state' in item && 'value' in item) return item.state === 'known' ? display(item.value) : states[item.state as FieldState]
    return <dl>{Object.entries(item).map(([key, val]) => <div key={key}><dt>{labels[key] ?? key}</dt><dd>{['kind', 'source_kind', 'field'].includes(key) && typeof val === 'string' ? labels[val] ?? val : display(val)}</dd></div>)}</dl>
  }
  return String(value)
}
export function DraftSummary({ values }: { values: Record<string, unknown> }) { return <div aria-label="Resumen de captura">{display(normalizeDraft(values))}</div> }
