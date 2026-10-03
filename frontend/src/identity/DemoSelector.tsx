const actors = [
  ['admision-demo', 'Admisión · demo'],
  ['supervisor-demo', 'Supervisor · demo'],
  ['consulta-demo', 'Consulta · demo'],
  ['inactivo-demo', 'Actor inactivo · demo'],
] as const

export default function DemoSelector({ actorKey, onChange }: { actorKey: string | null; onChange: (actor: string) => void }) {
  return <div className="demo-selector">
    <label htmlFor="demo-actor">Actor de demostración</label>
    <select id="demo-actor" value={actorKey ?? ''} onChange={event => onChange(event.target.value)}>
      {actors.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
    </select>
    <span>Identidad ficticia para pruebas locales</span>
  </div>
}
