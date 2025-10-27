/**
 * API Service for ROMS V2
 * Connects to the V2 backend (SQLite database)
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

export interface Order {
  id: number
  order_number: string
  product?: string
  price?: number
  total?: number
  commission?: number
  quantity?: number
  email?: string
  customer_name?: string
  profile?: string
  proxy_list?: string
  reference_number?: string
  status?: string
  tracking_number?: string
  qty_received?: number
  payment_method?: string
  shipping_address?: string
  shipping_method?: string
  notes?: string
  order_date?: string
  order_time?: string
  posted_date?: string
  shipped_date?: string
  delivered_date?: string
  source?: string
  worksheet_name?: string
  created_at: string
  updated_at: string
}

export interface OrdersResponse {
  orders: Order[]
  total: number
  page: number
  page_size: number
  has_next: boolean
  has_previous: boolean
}

/**
 * Fetch all orders with pagination and filtering
 */
export async function fetchOrders(
  page: number = 1,
  pageSize: number = 100,
  status?: string,
  search?: string
): Promise<OrdersResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  })

  if (status) params.append('status', status)
  if (search) params.append('search', search)

  const response = await fetch(`${API_BASE_URL}/api/v2/orders?${params}`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch orders: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Fetch single order by ID
 */
export async function fetchOrder(orderId: number): Promise<Order> {
  const response = await fetch(`${API_BASE_URL}/api/v2/orders/${orderId}`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch order: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Update an order
 */
export async function updateOrder(orderId: number, data: Partial<Order>): Promise<Order> {
  const response = await fetch(`${API_BASE_URL}/api/v2/orders/${orderId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    throw new Error(`Failed to update order: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Get webhook logs
 */
export async function fetchWebhookLogs(limit: number = 50) {
  const response = await fetch(`${API_BASE_URL}/api/v2/webhooks/logs?limit=${limit}`)
  
  if (!response.ok) {
    throw new Error(`Failed to fetch webhook logs: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Health check
 */
export async function checkHealth() {
  const response = await fetch(`${API_BASE_URL}/health`)
  
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`)
  }

  return response.json()
}

