import { useEffect } from 'react'

import { getCarePlanContent, getOrderStatus } from '../lib/api'

type UseOrderPollingArgs = {
  orderId: string
  setOrderStatus: (status: string) => void
  setCarePlanContent: (content: string) => void
  setIsPolling: (isPolling: boolean) => void
  setTimedOut: (timedOut: boolean) => void
  setError: (error: string) => void
}

export function useOrderPolling({
  orderId,
  setOrderStatus,
  setCarePlanContent,
  setIsPolling,
  setTimedOut,
  setError,
}: UseOrderPollingArgs) {
  useEffect(() => {
    if (!orderId) {
      return
    }

    const controller = new AbortController()
    let pollTimer: ReturnType<typeof setTimeout> | null = null
    let timeoutTimer: ReturnType<typeof setTimeout> | null = null
    let stopped = false

    const stopPolling = (updateState = true) => {
      stopped = true
      if (updateState) {
        setIsPolling(false)
      }
      if (pollTimer) {
        clearTimeout(pollTimer)
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
        const order = await getOrderStatus(orderId)

        if (stopped) {
          return
        }

        setOrderStatus(order.status)

        if (order.status === 'completed') {
          setTimedOut(false)
          stopPolling()
          try {
            const content = await getCarePlanContent(orderId, controller.signal)
            if (!controller.signal.aborted) {
              setCarePlanContent(content || 'Care plan completed, but content is not available yet.')
            }
          } catch {
            if (!controller.signal.aborted) {
              setError('Unable to load the completed care plan. Please refresh later.')
            }
          }
          return
        }

        if (order.status === 'failed') {
          setTimedOut(false)
          setError(order.error_message || 'Care plan generation failed. Please try again later.')
          stopPolling()
          return
        }
        pollTimer = setTimeout(pollOrder, 3000)
      } catch {
        if (stopped) return
        setError('Unable to refresh order status. Please refresh later.')
        stopPolling()
      }
    }

    // Polling reads Order.status while Celery updates the database asynchronously.
    setIsPolling(true)
    pollOrder()
    timeoutTimer = setTimeout(() => {
      setTimedOut(true)
      setError('Care plan is still processing. Please refresh later.')
      stopPolling()
    }, 90000)

    return () => {
      controller.abort()
      stopPolling(false)
    }
  }, [orderId, setCarePlanContent, setError, setIsPolling, setOrderStatus, setTimedOut])
}
