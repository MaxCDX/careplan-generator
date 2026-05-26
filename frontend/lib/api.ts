import type { FormData, OrderStatusResponse, QueuedOrder } from '../types/orders'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

export async function submitOrder(formData: FormData): Promise<QueuedOrder> {
  const orderResponse = await fetch(`${API_BASE_URL}/orders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData),
  })

  const orderData = await orderResponse.json()

  if (!orderResponse.ok) {
    throw new Error(orderData.detail || 'Order submission failed.')
  }

  return orderData
}

export async function getOrderStatus(orderId: string): Promise<OrderStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/orders/${orderId}/status`)
  const order: OrderStatusResponse = await response.json()

  if (!response.ok) {
    throw new Error('Unable to refresh order status.')
  }

  return order
}
