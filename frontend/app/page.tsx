'use client'

import { FormEvent, useState } from 'react'

type FormData = {
  patient_name: string
  mrn: string
  provider_name: string
  provider_npi: string
  diagnosis: string
  medication: string
  clinical_notes: string
}

const initialFormData: FormData = {
  patient_name: '',
  mrn: '',
  provider_name: '',
  provider_npi: '',
  diagnosis: '',
  medication: '',
  clinical_notes: '',
}

const fields: Array<{ name: keyof FormData; label: string; multiline?: boolean }> = [
  { name: 'patient_name', label: 'Patient name' },
  { name: 'mrn', label: 'MRN' },
  { name: 'provider_name', label: 'Provider name' },
  { name: 'provider_npi', label: 'Provider NPI' },
  { name: 'diagnosis', label: 'Diagnosis' },
  { name: 'medication', label: 'Medication' },
  { name: 'clinical_notes', label: 'Clinical notes', multiline: true },
]

export default function Home() {
  const [formData, setFormData] = useState<FormData>(initialFormData)
  const [carePlan, setCarePlan] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setCarePlan('')

    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

      // Day 3 flow step 1: create a durable Order workflow record first.
      const orderResponse = await fetch(`${apiBaseUrl}/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })

      const orderData = await orderResponse.json()

      if (!orderResponse.ok) {
        throw new Error(orderData.detail || 'Order creation failed.')
      }

      // Day 3 flow step 2: generate a CarePlan artifact from the saved order_id.
      const carePlanResponse = await fetch(`${apiBaseUrl}/care-plans`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_id: orderData.id }),
      })

      const carePlanData = await carePlanResponse.json()

      if (!carePlanResponse.ok) {
        throw new Error(carePlanData.detail || 'Care plan generation failed.')
      }

      setCarePlan(carePlanData.care_plan)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main style={{ maxWidth: 720, margin: '40px auto', padding: '0 16px', fontFamily: 'Arial, sans-serif' }}>
      <h1>Care Plan Generator</h1>

      <form onSubmit={handleSubmit} style={{ display: 'grid', gap: 12 }}>
        {fields.map((field) => (
          <label key={field.name} style={{ display: 'grid', gap: 4 }}>
            <span>{field.label}</span>
            {field.multiline ? (
              <textarea
                rows={5}
                value={formData[field.name]}
                onChange={(event) => setFormData({ ...formData, [field.name]: event.target.value })}
              />
            ) : (
              <input
                value={formData[field.name]}
                onChange={(event) => setFormData({ ...formData, [field.name]: event.target.value })}
              />
            )}
          </label>
        ))}

        <button type="submit" disabled={loading}>
          {loading ? 'Generating care plan...' : 'Generate care plan'}
        </button>
      </form>

      {error && <p style={{ color: 'crimson' }}>{error}</p>}

      {carePlan && (
        <section style={{ marginTop: 24 }}>
          <h2>Generated Care Plan</h2>
          <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{carePlan}</pre>
        </section>
      )}
    </main>
  )
}
