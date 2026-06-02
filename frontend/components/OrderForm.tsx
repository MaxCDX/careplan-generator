import type { SyntheticEvent } from 'react'

import type { FormData } from '../types/orders'

type OrderFormProps = {
  formData: FormData
  loading: boolean
  onChange: (name: keyof FormData, value: string) => void
  onSubmit: (event: SyntheticEvent<HTMLFormElement>) => void
}

type FormFieldName = Exclude<keyof FormData, 'confirm'>

const fields: Array<{ name: FormFieldName; label: string; multiline?: boolean; type?: string }> = [
  { name: 'patient_name', label: 'Patient name' },
  { name: 'patient_dob', label: 'Patient date of birth', type: 'date' },
  { name: 'mrn', label: 'MRN' },
  { name: 'provider_name', label: 'Provider name' },
  { name: 'provider_npi', label: 'Provider NPI' },
  { name: 'diagnosis', label: 'Diagnosis' },
  { name: 'medication', label: 'Medication' },
  { name: 'clinical_notes', label: 'Clinical notes', multiline: true },
]

export function OrderForm({ formData, loading, onChange, onSubmit }: OrderFormProps) {
  return (
    <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
      {fields.map((field) => (
        <label key={field.name} style={{ display: 'grid', gap: 4 }}>
          <span>{field.label}</span>
          {field.multiline ? (
            <textarea
              rows={5}
              value={formData[field.name]}
              onChange={(event) => onChange(field.name, event.target.value)}
            />
          ) : (
            <input
              type={field.type || 'text'}
              value={formData[field.name]}
              onChange={(event) => onChange(field.name, event.target.value)}
            />
          )}
        </label>
      ))}

      <button type="submit" disabled={loading}>
        {loading ? 'Submitting request...' : 'Submit care plan request'}
      </button>
    </form>
  )
}
