export type FormData = {
  patient_name: string
  mrn: string
  provider_name: string
  provider_npi: string
  diagnosis: string
  medication: string
  clinical_notes: string
}

export type QueuedOrder = {
  order_id: string
  status: string
  message: string
}

export type OrderStatusResponse = {
  id: string
  status: string
  error_message: string | null
  has_care_plan: boolean
  care_plan_content: string | null
}
