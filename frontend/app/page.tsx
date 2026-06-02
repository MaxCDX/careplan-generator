'use client'

import type { SyntheticEvent } from 'react'
import { useState } from 'react'

import { CarePlanResult } from '../components/CarePlanResult'
import { OrderForm } from '../components/OrderForm'
import { OrderStatus } from '../components/OrderStatus'
import { useOrderPolling } from '../hooks/useOrderPolling'
import { submitOrder } from '../lib/api'
import type { FormData, OrderSubmitResponse, QueuedOrder, WarningOrderResponse } from '../types/orders'

const initialFormData: FormData = {
  patient_name: '',
  patient_dob: '',
  mrn: '',
  provider_name: '',
  provider_npi: '',
  diagnosis: '',
  medication: '',
  clinical_notes: '',
}

export default function Home() {
  const [formData, setFormData] = useState<FormData>(initialFormData)
  const [queuedOrder, setQueuedOrder] = useState<QueuedOrder | null>(null)
  const [warningResponse, setWarningResponse] = useState<WarningOrderResponse | null>(null)
  const [pendingFormData, setPendingFormData] = useState<FormData | null>(null)
  const [orderId, setOrderId] = useState('')
  const [orderStatus, setOrderStatus] = useState('')
  const [carePlanContent, setCarePlanContent] = useState('')
  const [isPolling, setIsPolling] = useState(false)
  const [timedOut, setTimedOut] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const isTerminalStatus = orderStatus === 'completed' || orderStatus === 'failed'
  const shouldShowStatusMessage = !timedOut && (isPolling || isTerminalStatus)

  useOrderPolling({
    orderId,
    setOrderStatus,
    setCarePlanContent,
    setIsPolling,
    setTimedOut,
    setError,
  })

  function handleFormChange(name: keyof FormData, value: string) {
    setFormData({ ...formData, [name]: value })
  }

  function isWarningResponse(response: OrderSubmitResponse): response is WarningOrderResponse {
    return response.status === 'warning'
  }

  function handleSubmitResponse(response: OrderSubmitResponse, submittedFormData: FormData) {
    if (isWarningResponse(response)) {
      setWarningResponse(response)
      setPendingFormData(submittedFormData)
      setQueuedOrder(null)
      setOrderId('')
      setOrderStatus('')
      setCarePlanContent('')
      setIsPolling(false)
      setTimedOut(false)
      return
    }

    setWarningResponse(null)
    setPendingFormData(null)
    setQueuedOrder(response)
    setOrderId(response.order_id)
    setOrderStatus(response.status)
  }

  async function handleSubmit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setQueuedOrder(null)
    setWarningResponse(null)
    setPendingFormData(null)
    setOrderId('')
    setOrderStatus('')
    setCarePlanContent('')
    setIsPolling(false)
    setTimedOut(false)

    try {
      const orderData = await submitOrder(formData)

      handleSubmitResponse(orderData, formData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed.')
    } finally {
      setLoading(false)
    }
  }

  async function handleContinueAnyway() {
    if (!pendingFormData) {
      return
    }

    setLoading(true)
    setError('')

    try {
      const confirmedFormData = { ...pendingFormData, confirm: true }
      const orderData = await submitOrder(confirmedFormData)

      handleSubmitResponse(orderData, confirmedFormData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed.')
    } finally {
      setLoading(false)
    }
  }

  function handleCancelWarning() {
    setWarningResponse(null)
    setPendingFormData(null)
  }

  return (
    <main style={{ maxWidth: 720, margin: '40px auto', padding: '0 16px', fontFamily: 'Arial, sans-serif' }}>
      <h1>Care Plan Generator</h1>

      <OrderForm
        formData={formData}
        loading={loading}
        onChange={handleFormChange}
        onSubmit={handleSubmit}
      />

      {warningResponse && (
        <section style={{ marginTop: 24, border: '1px solid #f0b429', background: '#fff8e6', padding: 16 }}>
          <h2>Potential Duplicate Warning</h2>
          <ul>
            {warningResponse.warnings.map((warning) => (
              <li key={warning.code}>
                <strong>{warning.code}</strong>: {warning.message}
              </li>
            ))}
          </ul>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" onClick={handleContinueAnyway} disabled={loading}>
              {loading ? 'Submitting...' : 'Continue Anyway'}
            </button>
            <button type="button" onClick={handleCancelWarning} disabled={loading}>
              Cancel
            </button>
          </div>
        </section>
      )}

      <OrderStatus
        error={error}
        queuedOrder={queuedOrder}
        orderStatus={orderStatus}
        shouldShowStatusMessage={shouldShowStatusMessage}
        isPolling={isPolling}
      />

      <CarePlanResult carePlanContent={carePlanContent} />
    </main>
  )
}
