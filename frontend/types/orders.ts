export type FormData = {
  patient_name: string
  patient_dob: string
  mrn: string
  provider_name: string
  provider_npi: string
  diagnosis: string
  medication: string
  clinical_notes: string
  confirm?: boolean
}

export type QueuedOrder = {
  order_id: string
  status: string
  message: string
}

export type WarningItem = {
  code: string
  message: string
}

export type WarningOrderResponse = {
  status: 'warning'
  requires_confirmation: boolean
  warnings: WarningItem[]
}

export type ApiErrorResponse = {
  status: 'error'
  code: string
  message: string
  detail: unknown
}

export type OrderSubmitResponse = QueuedOrder | WarningOrderResponse

export type OrderStatusResponse = {
  id: string
  status: string
  error_message: string | null
  has_care_plan: boolean
  care_plan_content: string | null
}
