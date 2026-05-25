'use client'

import type { SyntheticEvent } from 'react'
import { useEffect, useState } from 'react'

type FormData = {
  patient_name: string
  mrn: string
  provider_name: string
  provider_npi: string
  diagnosis: string
  medication: string
  clinical_notes: string
}

type QueuedOrder = {
  order_id: string
  status: string
  message: string
}

type OrderStatusResponse = {
  id: string
  status: string
  error_message: string | null
  has_care_plan: boolean
  care_plan_content: string | null
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

const statusMessages: Record<string, string> = {
  queued: 'Request received. Waiting to start care plan generation.',
  processing: 'Generating care plan...',
  completed: 'Care plan ready.',
  failed: 'Care plan generation failed.',
}

function getStatusMessage(status: string) {
  return statusMessages[status] || 'Care plan request status is unavailable.'
}

export default function Home() {
  const [formData, setFormData] = useState<FormData>(initialFormData)
  const [queuedOrder, setQueuedOrder] = useState<QueuedOrder | null>(null)
  const [orderId, setOrderId] = useState('')
  const [orderStatus, setOrderStatus] = useState('')
  const [carePlanContent, setCarePlanContent] = useState('')
  const [isPolling, setIsPolling] = useState(false)
  const [timedOut, setTimedOut] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const isTerminalStatus = orderStatus === 'completed' || orderStatus === 'failed'
  const shouldShowStatusMessage = !timedOut && (isPolling || isTerminalStatus)

  useEffect(() => {
    if (!orderId) {
      return
    }

    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
    let pollTimer: ReturnType<typeof setInterval> | null = null
    let timeoutTimer: ReturnType<typeof setTimeout> | null = null
    let stopped = false

    const stopPolling = (updateState = true) => {
      stopped = true
      if (updateState) {
        setIsPolling(false)
      }
      if (pollTimer) {
        clearInterval(pollTimer)
      }
      if (timeoutTimer) {
        clearTimeout(timeoutTimer)
      }
    }

    async function pollOrder() {
      if (stopped) {
        return
      }

      try {
        const response = await fetch(`${apiBaseUrl}/orders/${orderId}/status`)
        const order: OrderStatusResponse = await response.json()

        if (!response.ok) {
          throw new Error('Unable to refresh order status.')
        }

        if (stopped) {
          return
        }

        setOrderStatus(order.status)

        if (order.status === 'completed') {
          setTimedOut(false)
          setCarePlanContent(order.care_plan_content || 'Care plan completed, but content is not available yet.')
          stopPolling()
        }

        if (order.status === 'failed') {
          setTimedOut(false)
          setError(order.error_message || 'Care plan generation failed. Please try again later.')
          stopPolling()
        }
      } catch {
        setError('Unable to refresh order status. Please refresh later.')
        stopPolling()
      }
    }

    // Day 6 polling reads Order.status while Celery updates the database asynchronously.
    setIsPolling(true)
    pollOrder()
    pollTimer = setInterval(pollOrder, 3000)
    timeoutTimer = setTimeout(() => {
      setTimedOut(true)
      setError('Care plan is still processing. Please refresh later.')
      stopPolling()
    }, 90000)

    return () => stopPolling(false)
  }, [orderId])

  async function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setQueuedOrder(null)
    setOrderId('')
    setOrderStatus('')
    setCarePlanContent('')
    setIsPolling(false)
    setTimedOut(false)

    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

      const orderResponse = await fetch(`${apiBaseUrl}/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })

      const orderData = await orderResponse.json()

      if (!orderResponse.ok) {
        throw new Error(orderData.detail || 'Order submission failed.')
      }

      setQueuedOrder(orderData)
      setOrderId(orderData.order_id)
      setOrderStatus(orderData.status)
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
          {loading ? 'Submitting request...' : 'Submit care plan request'}
        </button>
      </form>

      {error && <p style={{ color: 'crimson' }}>{error}</p>}

      {queuedOrder && (
        <section style={{ marginTop: 24 }}>
          <h2>Request Accepted</h2>
          <p>{queuedOrder.message}</p>
          <p>
            Order ID: <code>{queuedOrder.order_id}</code>
          </p>
          {shouldShowStatusMessage && <p>{getStatusMessage(orderStatus)}</p>}
          {isPolling && <p>This page will update automatically.</p>}
        </section>
      )}

      {carePlanContent && (
        <section style={{ marginTop: 24 }}>
          <h2>Generated Care Plan</h2>
          <pre style={{ whiteSpace: 'pre-wrap', border: '1px solid #ddd', padding: 16 }}>
            {carePlanContent}
          </pre>
        </section>
      )}
    </main>
  )
}
