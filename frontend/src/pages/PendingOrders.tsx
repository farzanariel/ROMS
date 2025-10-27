import { useQuery } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { useMediaQuery } from '../hooks/useMediaQuery'
import MobileOrderCard from '../components/MobileOrderCard'
import { 
  MagnifyingGlassIcon, 
  ExclamationTriangleIcon,
  ClockIcon,
  TruckIcon,
  XCircleIcon,
  CalendarIcon,
} from '@heroicons/react/24/outline'
import { fetchPendingOrders } from '../services/api'
import EditableOrderTable from '../components/EditableOrderTable'
import DateFilter, { DateFilterOption } from '../components/DateFilter'
import { useWebSocket } from '../hooks/useWebSocket'

interface PendingOrdersProps {
  sheetUrl: string
}

// Loading messages that cycle through
const LOADING_MESSAGES = [
  "Loading pending orders...",
  "Checking order status...",
  "Analyzing tracking numbers...",
  "Processing order data...",
  "Syncing with Google Sheets...",
  "Almost ready..."
]

export default function PendingOrders({ sheetUrl }: PendingOrdersProps) {
  const isMobile = useMediaQuery('(max-width: 640px)')
  const [searchTerm, setSearchTerm] = useState('')
  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set())
  const [loadingMessage, setLoadingMessage] = useState(LOADING_MESSAGES[0])
  const [loadingProgress, setLoadingProgress] = useState(0)
  const [showMobileSearch, setShowMobileSearch] = useState(false)
  const [selectedDateFilter, setSelectedDateFilter] = useState<DateFilterOption>(() => {
    try {
      const saved = localStorage.getItem('pending-orders-date-filter')
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

  // Enable real-time updates via WebSocket
  const { isConnected } = useWebSocket(sheetUrl)

  // Handle date filter changes
  const handleDateFilterChange = (filter: DateFilterOption, startDate?: string, endDate?: string) => {
    setSelectedDateFilter(filter)
    setCustomStartDate(startDate)
    setCustomEndDate(endDate)
    
    // Save to localStorage
    try {
      localStorage.setItem('pending-orders-date-filter', filter)
    } catch (error) {
      console.warn('Could not save to localStorage:', error)
    }
  }

  const { data: pendingData, isLoading, error, refetch } = useQuery({
    queryKey: ['pending-orders', sheetUrl, selectedDateFilter, customStartDate, customEndDate],
    queryFn: () => fetchPendingOrders(sheetUrl, selectedDateFilter, customStartDate, customEndDate),
    enabled: !!sheetUrl,
    refetchInterval: isConnected ? false : 120000, // 2 minutes when not connected
  })

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
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-md p-4">
            <div className="flex">
              <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                  Google Sheet URL Required
                </h3>
                <p className="mt-1 text-sm text-yellow-700 dark:text-yellow-300">
                  Please go to Settings and enter your Google Sheets URL to view pending orders.
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
              Loading Pending Orders
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
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-md p-4">
            <div className="flex">
              <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
                  Error Loading Pending Orders
                </h3>
                <p className="mt-1 text-sm text-red-700 dark:text-red-300">
                  {error instanceof Error ? error.message : 'Failed to load pending orders. Please check your Google Sheets URL and permissions.'}
                </p>
                <div className="mt-3">
                  <button
                    onClick={() => refetch()}
                    className="px-3 py-2 bg-red-600 text-white text-sm rounded hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!pendingData) return null

  // Get status counts for quick stats - only current month
  const currentMonth = new Date().getMonth()
  const currentYear = new Date().getFullYear()
  
  const currentMonthOrders = pendingData.pending_orders.filter((o: any) => {
    if (!o.Date) return false
    const orderDate = new Date(o.Date)
    return orderDate.getMonth() === currentMonth && orderDate.getFullYear() === currentYear
  })
  
  const noTracking = currentMonthOrders.filter((o: any) => !o['Tracking Number']).length
  const unverified = currentMonthOrders.filter((o: any) => o.Status?.toUpperCase() !== 'VERIFIED').length
  const partial = currentMonthOrders.filter((o: any) => o['QTY Received'] < o.Quantity).length

  // Filter toggle function
  const toggleFilter = (filterType: string) => {
    const newFilters = new Set(activeFilters)
    if (newFilters.has(filterType)) {
      newFilters.delete(filterType)
    } else {
      newFilters.add(filterType)
    }
    setActiveFilters(newFilters)
  }

  // Check if a filter is active
  const isFilterActive = (filterType: string) => activeFilters.has(filterType)

  // Filter pending orders based on search and KPI card filters
  // Use currentMonthOrders for filtering to match KPI card counts
  const filteredOrders = currentMonthOrders.filter((order: any) => {
    // First apply KPI card filters if any are active
    if (activeFilters.size > 0) {
      const passesFilters = Array.from(activeFilters).some(filterType => {
        switch (filterType) {
          case 'no-tracking':
            return !order['Tracking Number']
          case 'unverified':
            return order.Status?.toUpperCase() !== 'VERIFIED'
          case 'partial':
            return order['QTY Received'] < order.Quantity
          default:
            return false
        }
      })
      if (!passesFilters) return false
    }
    
    // Then apply search filter if search term exists
    if (searchTerm === '') return true
    
    // Search through all fields in the order
    return Object.values(order).some(value => 
      String(value).toLowerCase().includes(searchTerm.toLowerCase())
    )
  })

  return (
    <div className="p-4 sm:p-6 lg:p-8 pb-20 lg:pb-8">
      <div className="max-w-7xl mx-auto">
        {/* Header & Search */}
        <div className="relative mb-6 lg:mb-8">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between">
            <div className="flex-1">
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100">📦 Pending Orders</h1>
              <p className="mt-2 text-sm sm:text-base text-gray-600 dark:text-gray-300">
                Orders without tracking numbers - same format as your Google Sheets
              </p>
              
              {/* Date Filter */}
              <div className="mt-3">
                <DateFilter 
                  selectedFilter={selectedDateFilter}
                  onFilterChange={handleDateFilterChange}
                />
              </div>
              
              <div className="flex flex-col sm:flex-row sm:items-center mt-2 space-y-2 sm:space-y-0 sm:space-x-4">
                <div className="text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                  📋 {pendingData.total_pending} orders pending tracking | Updated: {new Date(pendingData.last_updated).toLocaleString()}
                </div>
                <div className="flex items-center space-x-1">
                  <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success-500 live-indicator' : 'bg-gray-400'}`}></div>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {isConnected ? 'Live sync enabled' : 'Cached data'}
                  </span>
                </div>
              </div>
            </div>
            
            {/* Desktop Search Bar - Always Visible */}
            <div className="hidden sm:block flex-shrink-0 mt-2 sm:mt-0 ml-4">
              <div className="relative max-w-md w-full">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="text"
                  placeholder="Search orders..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white dark:bg-gray-800 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-primary-500 focus:border-primary-500 text-sm"
                />
              </div>
            </div>
          </div>
          
          {/* Mobile Search - Icon and Expandable Bar */}
          <div className="sm:hidden absolute top-0 right-0">
            <div className="flex items-center">
              {/* Search Icon - Transforms and moves inside search bar */}
              <div className={`transition-all duration-300 ease-in-out ${showMobileSearch ? 'absolute left-3 top-1/2 -translate-y-1/2 z-10 flex items-center' : 'relative'}`}>
                <button
                  onClick={() => setShowMobileSearch(!showMobileSearch)}
                  className={`text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-all duration-300 ease-in-out ${showMobileSearch ? 'p-0' : 'p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800'}`}
                >
                  <MagnifyingGlassIcon className={`transition-all duration-300 ease-in-out ${showMobileSearch ? 'h-5 w-5 text-gray-400' : 'h-6 w-6'}`} />
                </button>
              </div>
              
              {/* Search Bar - Slides in from right */}
              <div className={`overflow-hidden transition-all duration-300 ease-in-out ${showMobileSearch ? 'w-64 opacity-100' : 'w-0 opacity-0'}`}>
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search orders..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white dark:bg-gray-800 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-primary-500 focus:border-primary-500 text-sm"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Current Month Summary */}
        <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <CalendarIcon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
                Current Month Focus: {new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
              </span>
            </div>
            <span className="text-xs text-blue-600 dark:text-blue-400">
              KPI cards show current month data only
            </span>
          </div>
        </div>



        {/* Quick Stats Cards - Clickable Filters */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 mb-6 lg:mb-8">
          <button
            onClick={() => toggleFilter('no-tracking')}
            className={`card border-l-4 transition-all duration-200 cursor-pointer hover:shadow-md ${
              isFilterActive('no-tracking') 
                ? 'border-l-warning-600 bg-warning-50 dark:bg-warning-900/20 ring-2 ring-warning-200 dark:ring-warning-700' 
                : 'border-l-warning-500 hover:border-l-warning-600'
            }`}
          >
            <div className="flex items-center">
              <ClockIcon className={`h-8 w-8 ${
                isFilterActive('no-tracking') 
                  ? 'text-warning-600 dark:text-warning-400' 
                  : 'text-warning-500 dark:text-warning-400'
              }`} />
              <div className="ml-4 text-left">
                <p className={`text-sm font-medium ${
                  isFilterActive('no-tracking') 
                    ? 'text-warning-700 dark:text-warning-200' 
                    : 'text-gray-600 dark:text-gray-300'
                }`}>
                  No Tracking (This Month)
                  {isFilterActive('no-tracking') && <span className="ml-2">✓</span>}
                </p>
                <p className={`text-2xl font-bold ${
                  isFilterActive('no-tracking') 
                    ? 'text-warning-700 dark:text-warning-200' 
                    : 'text-warning-600 dark:text-warning-400'
                }`}>{noTracking}</p>
              </div>
            </div>
          </button>
          
          <button
            onClick={() => toggleFilter('unverified')}
            className={`card border-l-4 transition-all duration-200 cursor-pointer hover:shadow-md ${
              isFilterActive('unverified') 
                ? 'border-l-danger-600 bg-danger-50 dark:bg-danger-900/20 ring-2 ring-danger-200 dark:ring-danger-700' 
                : 'border-l-danger-500 hover:border-l-danger-600'
            }`}
          >
            <div className="flex items-center">
              <XCircleIcon className={`h-8 w-8 ${
                isFilterActive('unverified') 
                  ? 'text-danger-600 dark:text-danger-400' 
                  : 'text-danger-600 dark:text-danger-400'
              }`} />
              <div className="ml-4 text-left">
                <p className={`text-sm font-medium ${
                  isFilterActive('unverified') 
                    ? 'text-danger-700 dark:text-danger-200' 
                    : 'text-gray-600 dark:text-gray-300'
                }`}>
                  Unverified (This Month)
                  {isFilterActive('unverified') && <span className="ml-2">✓</span>}
                </p>
                <p className={`text-2xl font-bold ${
                  isFilterActive('unverified') 
                    ? 'text-danger-700 dark:text-danger-200' 
                    : 'text-danger-600 dark:text-danger-400'
                }`}>{unverified}</p>
              </div>
            </div>
          </button>
          
          <button
            onClick={() => toggleFilter('partial')}
            className={`card border-l-4 transition-all duration-200 cursor-pointer hover:shadow-md ${
              isFilterActive('partial') 
                ? 'border-l-primary-600 bg-primary-50 dark:bg-primary-900/20 ring-2 ring-primary-200 dark:ring-primary-700' 
                : 'border-l-primary-500 hover:border-l-primary-600'
            }`}
          >
            <div className="flex items-center">
              <TruckIcon className={`h-8 w-8 ${
                isFilterActive('partial') 
                  ? 'text-primary-600 dark:text-primary-400' 
                  : 'text-primary-500 dark:text-primary-400'
              }`} />
              <div className="ml-4 text-left">
                <p className={`text-sm font-medium ${
                  isFilterActive('partial') 
                    ? 'text-primary-700 dark:text-primary-200' 
                    : 'text-gray-600 dark:text-gray-300'
                }`}>
                  Partial Received (This Month)
                  {isFilterActive('partial') && <span className="ml-2">✓</span>}
                </p>
                <p className={`text-2xl font-bold ${
                  isFilterActive('partial') 
                    ? 'text-primary-700 dark:text-primary-200' 
                    : 'text-primary-600 dark:text-primary-400'
                }`}>{partial}</p>
              </div>
            </div>
          </button>
        </div>

        {/* Filter Summary */}
        {activeFilters.size > 0 && (
          <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Active Filters:
                </span>
                <div className="flex space-x-2">
                  {Array.from(activeFilters).map(filterType => (
                    <span
                      key={filterType}
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 dark:bg-primary-900/30 text-primary-800 dark:text-primary-200"
                    >
                      {filterType === 'no-tracking' && 'No Tracking'}
                      {filterType === 'unverified' && 'Unverified'}
                      {filterType === 'partial' && 'Partial Received'}
                    </span>
                  ))}
                </div>
              </div>
              <button
                onClick={() => setActiveFilters(new Set())}
                className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 underline"
              >
                Clear All Filters
              </button>
            </div>
            <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Showing {filteredOrders.length} orders (filtered from {pendingData.total_pending} total)
            </div>
          </div>
        )}



        {/* Orders Display - Table for Desktop, Cards for Mobile */}
        {filteredOrders.length > 0 ? (
          isMobile ? (
            <div className="space-y-2">
              {filteredOrders.map((order: any, index: number) => (
                <MobileOrderCard
                  key={order['Order Number'] || index}
                  order={order}
                  onEdit={() => {
                    // Just refetch after any edit
                    refetch()
                  }}
                />
              ))}
            </div>
          ) : (
            <EditableOrderTable 
              orders={filteredOrders} 
              sheetUrl={sheetUrl}
              showPendingHighlight={true}
              onDataChange={() => refetch()}
            />
          )
        ) : (
          <div className="card text-center py-12">
            <ClockIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-semibold text-gray-900 dark:text-gray-100">No pending orders found</h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {searchTerm 
                ? 'Try adjusting your search criteria.'
                : 'All orders are up to date!'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
