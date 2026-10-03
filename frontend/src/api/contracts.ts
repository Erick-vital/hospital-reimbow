export interface Identity {
  id: string
  actor_key: string
  permissions: string[]
}

// Tipos de contexto básicos; la ficha administrativa ampliada pertenece a V2-04.
export interface PatientContext {
  id: string
  folio: string
  identity_status: 'provisional' | 'verified'
  given_names: string | null
  family_name: string | null
  second_family_name: string | null
  verification_quality: 'pending' | 'documented' | 'legacy_unsubstantiated'
}

export interface AdmissionContext {
  id: string
  folio: string
  patient_id: string
  type: 'emergency' | 'outpatient' | 'inpatient'
  status: 'open'
}
