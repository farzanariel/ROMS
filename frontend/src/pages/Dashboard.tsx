import { useQuery } from '@tanstack/react-query'
import {
  CurrencyDollarIcon,
  ShoppingCartIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  CalendarDaysIcon,
  EyeSlashIcon,
  EyeIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { fetchOrdersOverview, fetchOrdersOverviewQuick } from '../services/api'

import KPICard from '../components/KPICard'
import MonthlyRevenueChart from '../components/MonthlyRevenueChart'
import DateFilter, { DateFilterOption } from '../components/DateFilter'
import { useWebSocket } from '../hooks/useWebSocket'
import { useState, useEffect } from 'react'

interface DashboardProps {
  sheetUrl: string
}

const COLORS = ['#10b981', '#f59e0b', '#ef4444', '#6b7280']

// Loading messages that cycle through
const LOADING_MESSAGES = [
  "Loading order data...",
  "Calculating revenue metrics...",
  "Processing inventory status...",
  "Analyzing order patterns...",
  "Preparing performance charts...",
  "Syncing with Google Sheets...",
  "Almost ready..."
]

export default function Dashboard({ sheetUrl }: DashboardProps) {
  const [loadingMessage, setLoadingMessage] = useState(LOADING_MESSAGES[0])
  const [loadingProgress, setLoadingProgress] = useState(0)
  const [selectedDateFilter, setSelectedDateFilter] = useState<DateFilterOption>(() => {
    // Try to get from localStorage first, fallback to all_time
    try {
      const saved = localStorage.getItem('dashboard-selected-date-filter')
      if (saved && ['today', 'this_week', 'this_month', 'last_month', 'year_to_date', 'all_time', 'custom'].includes(saved)) {
        return saved as DateFilterOption
      }
    } catch (error) {
      console.warn('Could not read from localStorage:', error)
    }
    return 'all_time'
  })

  const [customStartDate, setCustomStartDate] = useState<string | undefined>()
  const [customEndDate, setCustomEndDate] = useState<string | undefined>()
  const [hiddenSections, setHiddenSections] = useState<Set<string>>(new Set())
  const [lastDataUpdate, setLastDataUpdate] = useState<Date | null>(null)
  const [showLayoutControls, setShowLayoutControls] = useState(false)
  const [showDateRange, setShowDateRange] = useState(false)
  const [debugMode] = useState(() => localStorage.getItem('debug-mode') === 'true')
  const [cacheDuration] = useState(() => parseInt(localStorage.getItem('cache-duration') || '5', 10))
  
  // Enable real-time updates via WebSocket
  const { isConnected } = useWebSocket(sheetUrl)
  
  // Handle date filter changes
  const handleDateFilterChange = (filter: DateFilterOption, startDate?: string, endDate?: string) => {
    setSelectedDateFilter(filter)
    setCustomStartDate(startDate)
    setCustomEndDate(endDate)

    try {
      localStorage.setItem('dashboard-selected-date-filter', filter)
      if (startDate) localStorage.setItem('dashboard-custom-start-date', startDate)
      if (endDate) localStorage.setItem('dashboard-custom-end-date', endDate)
    } catch (error) {
      console.warn('Could not save to localStorage:', error)
    }
  }

  // Construct query based on date filter
  const getDateRangeParams = () => {
    const params: Record<string, string> = {}

    if (selectedDateFilter === 'custom' && customStartDate && customEndDate) {
      params.start_date = customStartDate
      params.end_date = customEndDate
    } else {
      params.date_filter = selectedDateFilter
    }

    return params
  }

  // PROGRESSIVE LOADING: Quick data first, then full data
  const { data: quickOverview, isLoading: isLoadingQuick } = useQuery({
    queryKey: ['orders-overview-quick', sheetUrl],
    queryFn: () => fetchOrdersOverviewQuick(sheetUrl),
    enabled: !!sheetUrl && selectedDateFilter === 'all_time', // Only for all_time view
    staleTime: 30000, // Keep quick data fresh for 30 seconds
    gcTime: 60000, // Cache quick data for 1 minute
  })

  const { data: fullOverview, isLoading: isLoadingFull, error } = useQuery({
    queryKey: ['orders-overview', sheetUrl, selectedDateFilter, customStartDate, customEndDate],
    queryFn: () => {
      const params = getDateRangeParams()
      return fetchOrdersOverview(sheetUrl, params)
    },
    enabled: !!sheetUrl,
    refetchInterval: isConnected ? false : 120000, // 2 minutes when not connected, let WebSocket handle when connected
    staleTime: cacheDuration * 1000, // Use user-defined cache duration in seconds
    gcTime: cacheDuration * 60000, // Cache data for user-defined duration in minutes
    refetchOnWindowFocus: false, // Don't refetch when tab becomes active
    refetchOnMount: false, // Don't refetch when component mounts if data exists
  })

  // Use progressive data: quick first, then full when available
  const overview = fullOverview || quickOverview
  const isLoading = !overview && (isLoadingQuick || isLoadingFull)
  const isUpgrading = quickOverview && isLoadingFull && !fullOverview // Upgrading from quick to full

  // Load hidden sections from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('dashboard-hidden-sections')
    if (saved) {
      setHiddenSections(new Set(JSON.parse(saved)))
    }
  }, [])

  // Save hidden sections to localStorage
  useEffect(() => {
    localStorage.setItem('dashboard-hidden-sections', JSON.stringify(Array.from(hiddenSections)))
  }, [hiddenSections])

  // Track data updates for visual indicators
  useEffect(() => {
    if (overview && !isLoading) {
      setLastDataUpdate(new Date())
      
      if (debugMode) {
        console.log('🔍 Dashboard Debug - Data Updated:', {
          timestamp: new Date().toISOString(),
          selectedDateFilter,
          customStartDate,
          customEndDate,
          overview: overview?.overview,
          lastUpdate: overview?.last_updated,
          // Add specific KPI values for debugging
          todaysRevenue: overview?.overview?.todays_revenue,
          monthlyRevenue: overview?.overview?.monthly_revenue,
          totalRevenue: overview?.overview?.total_revenue,
          currentMonthProfit: overview?.overview?.current_month_profit,
          currentMonthOrders: overview?.overview?.current_month_orders,
          currentMonthShipped: overview?.overview?.current_month_shipped
        })
      }
    }
  }, [overview, isLoading, debugMode, selectedDateFilter, customStartDate, customEndDate])

  // Section visibility functions
  const toggleSection = (sectionId: string) => {
    const newHidden = new Set(hiddenSections)
    if (newHidden.has(sectionId)) {
      newHidden.delete(sectionId)
    } else {
      newHidden.add(sectionId)
    }
    setHiddenSections(newHidden)
  }

  const isSectionHidden = (sectionId: string) => hiddenSections.has(sectionId)

  // Progress bar and loading message animation
  useEffect(() => {
    if (isLoading) {
      let progress = 0
      let messageIndex = 0
      
      const progressInterval = setInterval(() => {
        progress += Math.random() * 15 + 5 // Random progress increment
        if (progress >= 90) progress = 90 // Cap at 90% until complete
        setLoadingProgress(progress)
      }, 200)
      
      const messageInterval = setInterval(() => {
        messageIndex = (messageIndex + 1) % LOADING_MESSAGES.length
        setLoadingMessage(LOADING_MESSAGES[messageIndex])
      }, 1500)
      
      return () => {
        clearInterval(progressInterval)
        clearInterval(messageInterval)
      }
    } else {
      setLoadingProgress(100)
      setLoadingMessage("Ready!")
    }
  }, [isLoading])

  if (!sheetUrl) {
    return (
      <div className="p-8">
        <div className="max-w-4xl mx-auto">
          <div className="bg-warning-50 border border-warning-200 rounded-md p-4">
            <div className="flex">
              <ExclamationTriangleIcon className="h-5 w-5 text-warning-400" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-warning-800">
                  Google Sheet URL Required
                </h3>
                <p className="mt-1 text-sm text-warning-700">
                  Please go to Settings and enter your Google Sheets URL to view your order data.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="max-w-md w-full text-center">
          {/* Progress Bar */}
          <div className="mb-6">
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 mb-4">
              <div 
                className="bg-blue-600 h-3 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${loadingProgress}%` }}
              ></div>
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              {Math.round(loadingProgress)}% Complete
            </div>
          </div>
          
          {/* Loading Message */}
          <div className="mb-8">
            <div className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              Loading Dashboard
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-300">
              {loadingMessage}
            </div>
          </div>
          
          {/* Loading Animation */}
          <div className="flex justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="max-w-4xl mx-auto">
          <div className="bg-danger-50 border border-danger-200 rounded-md p-4">
            <div className="flex">
              <ExclamationTriangleIcon className="h-5 w-5 text-danger-400" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-danger-800">
                  Error Loading Data
                </h3>
                <p className="mt-1 text-sm text-danger-700">
                  Failed to load order data. Please check your Google Sheets URL and permissions.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Enhanced error handling for API responses
  if (error || !overview || !overview.status_breakdown || !overview.top_products) {
    if (error) {
      console.error('Dashboard error:', error)
    }
    if (overview && (!overview.status_breakdown || !overview.top_products)) {
      console.error('Dashboard received invalid data structure:', overview)
    }

    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="text-center">
              <div className="text-red-500 dark:text-red-400 mb-4">
                <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 15.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                Unable to Load Dashboard Data
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                There was a problem loading your dashboard data. This might be due to:
              </p>
              <ul className="text-sm text-gray-600 dark:text-gray-400 mb-4 text-left max-w-md mx-auto">
                <li>• Invalid Google Sheets URL or permissions</li>
                <li>• Network connectivity issues</li>
                <li>• Server configuration problems</li>
              </ul>
              {error && (
                <p className="text-xs text-red-500 dark:text-red-400 mb-4">
                  Error: {(error as Error)?.message || 'Unknown error occurred'}
                </p>
              )}
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Prepare chart data with safe property access
  const statusData = Object.entries(overview.status_breakdown || {}).map(([status, count]) => ({
    status,
    count
  }))

  const productData = Object.entries(overview.top_products || {}).slice(0, 5).map(([product, count]) => ({
    product: product.length > 20 ? product.substring(0, 20) + '...' : product,
    count
  }))

  return (
    <div className="p-3 sm:p-5 lg:p-6 pb-16 lg:pb-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-3">
          {/* Header with Title and Gear Icon - Properly separated */}
          <div className="flex items-start justify-between mb-3">
            <div className="flex-1">
              <h1 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-gray-100">Welcome, {overview?.account_name || 'Dashboard User'}! 👋</h1>
              <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-4 mt-1 space-y-1 sm:space-y-0">
                <p className="text-xs text-gray-600 dark:text-gray-300">
                  Today's performance and pending orders overview
                </p>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  📅 {overview?.todays_date ? new Date(overview.todays_date).toLocaleDateString() : new Date().toLocaleDateString()} | Last updated: {overview?.last_updated ? new Date(overview.last_updated).toLocaleString() : 'Unknown'}
                </div>
                <div className="flex items-center space-x-1">
                  <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success-500 live-indicator' : 'bg-gray-400'}`}></div>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {isConnected ? 'Live data' : 'Reconnecting...'}
                  </span>
                </div>
              </div>
            </div>
            
            {/* Gear Icon - Positioned in top right corner, separate from text flow */}
            <div className="flex-shrink-0 ml-3">
              <button
                onClick={() => {
                  setShowDateRange(!showDateRange)
                  setShowLayoutControls(!showLayoutControls)
                }}
                className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
                title="Settings"
              >
                <Cog6ToothIcon className="h-5 w-5" />
              </button>
            </div>
          </div>

          {/* Date Range Selector - Hidden by default */}
          {showDateRange && (
            <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center space-x-2">
                <CalendarDaysIcon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Date Range:</span>
                {selectedDateFilter !== 'all_time' && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200">
                    Filtered
                  </span>
                )}
              </div>
              
              <div className="w-48">
                <DateFilter
                  selectedFilter={selectedDateFilter}
                  onFilterChange={handleDateFilterChange}
                />
              </div>
            </div>
          </div>
          )}

          {/* Layout Controls Panel */}
          {showLayoutControls && (
            <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700">
              <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">Layout Controls</h3>
              <div className="flex flex-wrap gap-2">
                {[
                  { id: 'revenue', label: 'Revenue Overview' },
                  { id: 'performance', label: 'Monthly Performance' },
                  { id: 'inventory', label: 'Inventory Status' },
                  { id: 'charts', label: 'Charts' }
                ].map((section) => (
                  <button
                    key={section.id}
                    onClick={() => toggleSection(section.id)}
                    className={`flex items-center space-x-1 px-3 py-1 text-xs rounded-full transition-colors ${
                      isSectionHidden(section.id)
                        ? 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
                        : 'bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-200'
                    }`}
                  >
                    {isSectionHidden(section.id) ? (
                      <EyeSlashIcon className="h-3 w-3" />
                    ) : (
                      <EyeIcon className="h-3 w-3" />
                    )}
                    <span>{section.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Progressive Loading Indicator - Only show when needed */}
          {(isUpgrading || overview?.overview?.is_partial) && (
            <div className="mt-3 flex items-center space-x-1">
              <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
              <span className="text-xs text-blue-600 dark:text-blue-400">
                {overview?.overview?.message || 'Loading full data...'}
              </span>
            </div>
          )}

          {/* No Data Message - Show when there are no orders for the selected date range */}
          {!isUpgrading && overview?.overview?.total_orders === 0 && overview?.message && (
            <div className="mt-3 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200">
                    No Orders Found
                  </h3>
                  <p className="mt-1 text-sm text-blue-700 dark:text-blue-300">
                    {overview.message}
                  </p>
                  <p className="mt-1 text-xs text-blue-600 dark:text-blue-400">
                    Try selecting a different date range or check back later for new orders.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Debug Panel */}
        {debugMode && overview && (
          <div className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-700">
            <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200 mb-2">🔍 Debug Information</h3>
            <div className="text-xs text-yellow-700 dark:text-yellow-300 space-y-1">
              <div><strong>Date Filter:</strong> {selectedDateFilter} {selectedDateFilter === 'custom' && `(${customStartDate} to ${customEndDate})`}</div>
              <div><strong>Total Orders:</strong> {overview?.overview?.total_orders || 0}</div>
              <div><strong>Last API Call:</strong> {overview?.last_updated ? new Date(overview.last_updated).toLocaleString() : 'Unknown'}</div>
              <div><strong>Cache Key:</strong> orders-overview-{sheetUrl}-{selectedDateFilter}-{customStartDate}-{customEndDate}</div>
              <div><strong>WebSocket:</strong> {isConnected ? 'Connected' : 'Disconnected'}</div>
            </div>
          </div>
        )}

        {/* REVENUE OVERVIEW - Primary Focus */}
        {!isSectionHidden('revenue') && (
        <div className="mb-3">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3 lg:gap-4">
            {/* Mobile-first order: Today's Revenue first, then Monthly, then Total */}
            <KPICard
              title="Today's Revenue"
              value={overview?.overview?.todays_revenue || "$0.00"}
              icon={<CurrencyDollarIcon className="h-6 w-6 text-amber-500 dark:text-amber-300" />}
              color="warning"
            />
            <KPICard
              title={`${new Date().toLocaleDateString('en-US', { month: 'long' })} Revenue`}
              value={overview?.overview?.monthly_revenue || "$0.00"}
              icon={<CurrencyDollarIcon className="h-6 w-6 text-emerald-500 dark:text-emerald-300" />}
              color="success"
            />
            <KPICard
              title="Total Revenue"
              value={overview?.overview?.total_revenue || "$0.00"}
              icon={<CurrencyDollarIcon className="h-6 w-6 text-blue-500 dark:text-blue-300" />}
              color="primary"
            />
            <KPICard
              title="Profit"
              value={overview?.overview?.current_month_profit || "$0.00"}
              icon={<CurrencyDollarIcon className="h-6 w-6 text-emerald-500 dark:text-emerald-300" />}
              color="success"
            />
          </div>
        </div>
        )}

        {/* MONTHLY REVENUE CHART */}
        {!isSectionHidden('performance') && (
        <div className="mb-3 lg:mb-4 -mx-3 sm:-mx-5 lg:-mx-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700 mx-3 sm:mx-5 lg:mx-6">
            <MonthlyRevenueChart sheetUrl={sheetUrl} />
          </div>
        </div>
        )}

        {/* Inventory Status Cards - Your main pain point */}
        {!isSectionHidden('inventory') && (
        <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-3 gap-1.5 sm:gap-2 lg:gap-3 mb-4 lg:mb-6">
          <div className="card">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">Quantity Overview</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-300">Total Ordered:</span>
                <span className="font-semibold text-base text-gray-900 dark:text-gray-100">{overview?.overview?.total_quantity || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-300">Received:</span>
                <span className="font-semibold text-base text-success-600">{overview?.overview?.received_quantity || 0}</span>
              </div>
              <div className="flex justify-between items-center border-t border-gray-200 dark:border-gray-600 pt-3">
                <span className="text-gray-600 dark:text-gray-300">Pending:</span>
                <span className="font-semibold text-base text-warning-600">{overview?.overview?.pending_quantity || 0}</span>
              </div>
            </div>
          </div>

          <div className="card">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">Completion Rate</h3>
            <div className="text-center">
              <div className="text-xl font-bold text-primary-600">
                {overview.overview.total_quantity > 0 
                  ? Math.round((overview.overview.received_quantity / overview.overview.total_quantity) * 100)
                  : 0}%
              </div>
              <p className="text-gray-600 dark:text-gray-300 mt-2">Orders Fulfilled</p>
            </div>
          </div>

          <div className="card">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">Recent Activity</h3>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-300">This Week:</span>
                <span className="font-semibold text-gray-900 dark:text-gray-100">{overview.recent_orders_count} orders</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-300">Today:</span>
                <span className="font-semibold text-gray-900 dark:text-gray-100">{overview.overview.orders_today} orders</span>
              </div>
            </div>
          </div>
        </div>
        )}

        {/* Charts */}
        {!isSectionHidden('charts') && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-2 lg:gap-4 mb-4 lg:mb-6">
          {/* Order Status Breakdown */}
          <div className="card">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">Order Status Distribution</h3>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ status, percent }) => `${status} (${(percent * 100).toFixed(0)}%)`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="count"
                >
                  {statusData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Top Products */}
          <div className="card">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">Top Products</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={productData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="product" 
                  angle={-45}
                  textAnchor="end"
                  height={100}
                />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        )}
      </div>
    </div>
  )
}
