import type { QueuedOrder } from '../types/orders'

type OrderStatusProps = {
  error: string
  queuedOrder: QueuedOrder | null
  orderStatus: string
  shouldShowStatusMessage: boolean
  isPolling: boolean
}

const statusMessages: Record<string, string> = {
  queued: 'Request received. Waiting to start care plan generation.',
  processing: 'Generating care plan...',
  completed: 'Care plan ready.',
  failed: 'Care plan generation failed.',
}

function getStatusMessage(status: string) {
  return statusMessages[status] || 'Care plan request status is unavailable.'
}

export function OrderStatus({
  error,
  queuedOrder,
  orderStatus,
  shouldShowStatusMessage,
  isPolling,
}: OrderStatusProps) {
  return (
    <>
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
    </>
  )
}
