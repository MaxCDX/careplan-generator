import { useEffect } from 'react'

import { getOrderStatus } from '../lib/api'

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
        const order = await getOrderStatus(orderId)

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
  }, [orderId, setCarePlanContent, setError, setIsPolling, setOrderStatus, setTimedOut])
}
