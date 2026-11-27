import type { ApiErrorResponse, FormData, OrderStatusResponse, OrderSubmitResponse } from '../types/orders'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

export async function submitOrder(formData: FormData): Promise<OrderSubmitResponse> {
  const orderResponse = await fetch(`${API_BASE_URL}/orders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData),
  })

  const orderData = await orderResponse.json()

  if (!orderResponse.ok) {
    const errorData = orderData as Partial<ApiErrorResponse>
    throw new Error(errorData.message || 'Order submission failed.')
  }

  return orderData as OrderSubmitResponse
}

export async function getOrderStatus(orderId: string): Promise<OrderStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/orders/${orderId}/status`)
  const order: OrderStatusResponse = await response.json()

  if (!response.ok) {
    throw new Error('Unable to refresh order status.')
  }

  return order
}

export async function getCarePlanContent(orderId: string, signal: AbortSignal): Promise<string | null> {
  const response = await fetch(`${API_BASE_URL}/orders/${orderId}`, { signal })
  if (!response.ok) {
    throw new Error('Unable to load the completed care plan.')
  }
  const order: { care_plan_content: string | null } = await response.json()
  return order.care_plan_content
}
