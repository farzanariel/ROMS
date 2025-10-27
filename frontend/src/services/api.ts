import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000, // 30 second timeout
})

export interface DetailedProduct {
  order_count: number
  total_revenue: number
  total_profit: number
  total_quantity: number
  shipped_count: number
  avg_price: number
  avg_profit: number
  fulfillment_rate: number
}

export interface OrdersOverview {
  overview: {
    total_orders: number
    total_revenue: string
    orders_today: number
    pending_orders: number
    pending_quantity: number
    total_quantity: number
    received_quantity: number
    // New current month KPI metrics
    current_month_orders: number
    current_month_shipped: number
    current_month_packages_scanned: number
    current_month_missing_packages: number
    current_month_profit: string
    // Previous month KPI metrics for comparison
    previous_month_orders: number
    previous_month_shipped: number
    previous_month_packages_scanned: number
    previous_month_missing_packages: number
    previous_month_profit: string
    // Legacy fields for compatibility
    todays_revenue?: string
    todays_orders?: number
    monthly_revenue?: string
    total_worksheets?: number
    // Progressive loading indicators
    is_partial?: boolean
    message?: string
  }
  status_breakdown: Record<string, number>
  top_products: Record<string, number>
  detailed_products: Record<string, DetailedProduct>
  recent_orders_count: number
  last_updated: string
  account_name?: string
  todays_date?: string
  message?: string  // Top-level message for empty data states
  data_source?: string  // Source indicator (e.g., "empty", "filtered")
}

export interface PendingOrdersResponse {
  pending_orders: any[]
  total_pending: number
  last_updated: string
}

export interface AllOrdersResponse {
  orders: any[]
  total_records: number
  limit: number
  offset: number
  has_next: boolean
  last_updated: string
}

export interface MonthlyRevenueResponse {
  monthly_data: Array<{
    month: string
    revenue: number
    year: number
    month_num: number
  }>
  last_updated: string
}

export interface CellUpdateRequest {
  row_id: string
  column: string
  value: string
}

export interface RowUpdateRequest {
  row_id: string
  data: Record<string, any>
}

export interface NewOrderRequest {
  data: Record<string, any>
}

// Read operations
export const fetchOrdersOverview = async (
  sheetUrl: string, 
  additionalParams: Record<string, string> = {}
): Promise<OrdersOverview> => {
  if (!sheetUrl) {
    throw new Error('Sheet URL is required')
  }
  
  const response = await api.get('/orders/overview', {
    params: { 
      sheet_url: sheetUrl,
      ...additionalParams
    }
  })
  return response.data
}

export const fetchOrdersOverviewQuick = async (sheetUrl: string): Promise<OrdersOverview> => {
  if (!sheetUrl) {
    throw new Error('Sheet URL is required')
  }
  
  const response = await api.get('/orders/overview/quick', {
    params: { sheet_url: sheetUrl }
  })
  return response.data
}

export const fetchPendingOrders = async (
  sheetUrl: string,
  date_filter?: string,
  start_date?: string,
  end_date?: string
): Promise<PendingOrdersResponse> => {
  if (!sheetUrl) {
    throw new Error('Sheet URL is required')
  }
  
  const params: any = { sheet_url: sheetUrl }
  if (date_filter && date_filter !== 'all_time') {
    params.date_filter = date_filter
  }
  if (start_date) params.start_date = start_date
  if (end_date) params.end_date = end_date
  
  const response = await api.get('/orders/pending', { params })
  return response.data
}

export const fetchAllOrders = async (
  sheetUrl: string, 
  limit: number = 100, 
  offset: number = 0,
  worksheet?: string,
  date_filter?: string,
  start_date?: string,
  end_date?: string
): Promise<AllOrdersResponse> => {
  if (!sheetUrl) {
    throw new Error('Sheet URL is required')
  }
  
  const params: any = { 
    sheet_url: sheetUrl,
    limit,
    offset
  }
  if (worksheet) {
    params.worksheet = worksheet
  }
  if (date_filter && date_filter !== 'all_time') {
    params.date_filter = date_filter
  }
  if (start_date) params.start_date = start_date
  if (end_date) params.end_date = end_date
  
  const response = await api.get('/orders/all', { params })
  return response.data
}

export const checkHealth = async () => {
  const response = await api.get('/health')
  return response.data
}

// Worksheet management operations
export interface WorksheetInfo {
  id: string | number
  title: string
  index: number
  row_count: number
  col_count: number
  data_rows: number
  url: string
  updated: string | null
  sheet_type: 'orders' | 'data' | 'unknown'
  error?: string
}

export interface WorksheetConfig {
  enabled: boolean
  custom_name?: string
  priority: number
  refresh_interval: number
  include_in_dashboard: boolean
  include_in_reports: boolean
  color_theme?: string
  notes?: string
}

export interface WorksheetsResponse {
  worksheets: WorksheetInfo[]
  total_count: number
  last_updated: string
}

export interface WorksheetConfigResponse {
  configurations: Record<string, WorksheetConfig>
  last_updated: string
}

export const fetchWorksheets = async (sheetUrl: string): Promise<WorksheetsResponse> => {
  if (!sheetUrl) {
    throw new Error('Sheet URL is required')
  }
  
  const response = await api.get('/worksheets', {
    params: { sheet_url: sheetUrl }
  })
  return response.data
}

export const fetchWorksheetConfig = async (): Promise<WorksheetConfigResponse> => {
  const response = await api.get('/worksheets/config')
  return response.data
}

export const updateWorksheetConfig = async (configurations: Record<string, WorksheetConfig>) => {
  const response = await api.post('/worksheets/config', {
    configurations
  })
  return response.data
}

// Write operations - New functionality for editable tables
export const updateCell = async (sheetUrl: string, request: CellUpdateRequest) => {
  if (!sheetUrl) {
    throw new Error('Sheet URL is required')
  }
  
  const response = await api.put('/orders/cell', request, {
    params: { sheet_url: sheetUrl }
  })
  return response.data
}

export const updateRow = async (sheetUrl: string, request: RowUpdateRequest) => {
  if (!sheetUrl) {
    throw new Error('Sheet URL is required')
  }
  
  const response = await api.put('/orders/row', request, {
    params: { sheet_url: sheetUrl }
  })
  return response.data
}

export const createOrder = async (sheetUrl: string, request: NewOrderRequest) => {
  if (!sheetUrl) {
    throw new Error('Sheet URL is required')
  }
  
  const response = await api.post('/orders/new', request, {
    params: { sheet_url: sheetUrl }
  })
  return response.data
}

// File processing operations
export type FileAction = "upload_orders" | "cancel_orders" | "upload_trackings" | "mark_received" | "reconcile_charges";

export interface FileProcessResponse {
  message: string;
  processed_count: number;
  failed_count: number;
  // Can be expanded with more details later
}

export const processFile = async (
  sheetUrl: string,
  action: FileAction,
  file: File,
  client_id: string,
  worksheet_name?: string
): Promise<FileProcessResponse> => {
  if (!sheetUrl) {
    throw new Error('Sheet URL is required');
  }
  if (!file) {
    throw new Error('File is required');
  }

  const formData = new FormData();
  formData.append('sheet_url', sheetUrl);
  formData.append('action', action);
  formData.append('file', file);
  formData.append('client_id', client_id);
  if (worksheet_name) {
    formData.append('worksheet_name', worksheet_name);
  }

  const response = await api.post('/files/process', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 300000, // 5 minute timeout for potentially large files
  });

  return response.data;
};

export const fetchMonthlyRevenue = async (sheetUrl: string): Promise<MonthlyRevenueResponse> => {
  if (!sheetUrl) {
    throw new Error('Sheet URL is required')
  }
  
  const response = await api.get('/analytics/monthly-revenue', {
    params: { sheet_url: sheetUrl }
  })
  return response.data
}