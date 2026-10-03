export interface Identity { id: string; actor_key: string; permissions: string[] }
export type FieldState = 'known' | 'unknown' | 'not_provided' | 'not_applicable'
export interface Field<T> { state: FieldState; value: T | null }
export interface PatientContext {
  id: string; folio: string; identity_status: 'provisional' | 'verified'
  given_names: string | null; family_name: string | null; second_family_name: string | null
  verification_quality: 'pending' | 'documented' | 'legacy_unsubstantiated'
  birth_date?: string | null
  identifiers?: { system: string; value: string }[]
  created_at?: string
  administrative_origin?: 'v2' | 'legacy'
  is_unidentified?: boolean | null
  identity_field_states?: Record<string, FieldState>
  administrative_profile?: {
    registered_sex: Field<string>; nationality: Field<string>
    phones: Field<{ kind: string; number: string }[]>
    addresses: Field<{ kind: string; street: string | null; exterior: string | null; interior: string | null; neighborhood: string | null; postal_code: string | null; municipality: string | null; state: string | null; country: string | null; references: string | null }[]>
    emergency_contacts: Field<{ name: string; relationship: Field<string>; phone: Field<string> }[]>
  }
  unidentified_description?: {
    apparent_sex: Field<string>; estimated_age: Field<{ min_years: number; max_years: number }>
    identifying_features: Field<string>; origin: Field<string>; transferred_by: Field<string>
  }
}
export interface AdmissionContext {
  id: string; folio: string; patient_id: string
  type: 'emergency' | 'outpatient' | 'inpatient'; status: 'open'; created_at: string
  intake_origin?: 'v2' | 'legacy'
  intake?: { admitted_at: Field<string>; site_id: Field<string>; service_id: Field<string>; origin: Field<string>; reason_for_visit: Field<string> }
}
export interface PageResult<T> { items: T[]; limit: number; offset: number; total: number }
export interface PatientPage extends PageResult<PatientContext> { search_id: string }
