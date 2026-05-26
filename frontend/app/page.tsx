'use client'

import type { SyntheticEvent } from 'react'
import { useState } from 'react'

import { CarePlanResult } from '../components/CarePlanResult'
import { OrderForm } from '../components/OrderForm'
import { OrderStatus } from '../components/OrderStatus'
import { useOrderPolling } from '../hooks/useOrderPolling'
import { submitOrder } from '../lib/api'
import type { FormData, QueuedOrder } from '../types/orders'

const initialFormData: FormData = {
  patient_name: '',
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
      const orderData = await submitOrder(formData)

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

      <OrderForm
        formData={formData}
        loading={loading}
        onChange={handleFormChange}
        onSubmit={handleSubmit}
      />

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
