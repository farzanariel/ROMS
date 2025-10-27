import { useQuery } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { 
  MagnifyingGlassIcon, 
  ExclamationTriangleIcon,
  DocumentTextIcon
} from '@heroicons/react/24/outline'
import { fetchAllOrders } from '../services/api'
import EditableOrderTable from '../components/EditableOrderTable'
import MobileOrderCard from '../components/MobileOrderCard'
import DateFilter, { DateFilterOption } from '../components/DateFilter'
import { useWebSocket } from '../hooks/useWebSocket'
import { useMediaQuery } from '../hooks/useMediaQuery'

interface AllOrdersProps {
  sheetUrl: string
}

// Loading messages that cycle through
const LOADING_MESSAGES = [
  "Loading all orders...",
  "Processing order data...",
  "Analyzing order details...",
  "Preparing order table...",
  "Syncing with Google Sheets...",
  "Almost ready..."
]

export default function AllOrders({ sheetUrl }: AllOrdersProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [loadingMessage, setLoadingMessage] = useState(LOADING_MESSAGES[0])
  const [loadingProgress, setLoadingProgress] = useState(0)
  const [showMobileSearch, setShowMobileSearch] = useState(false)
  const [selectedDateFilter, setSelectedDateFilter] = useState<DateFilterOption>(() => {
    try {
      const saved = localStorage.getItem('all-orders-date-filter')
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

  // Check if we're on mobile
  const isMobile = useMediaQuery('(max-width: 640px)')

  // Enable real-time updates via WebSocket
  const { isConnected } = useWebSocket(sheetUrl)

  // Handle date filter changes
  const handleDateFilterChange = (filter: DateFilterOption, startDate?: string, endDate?: string) => {
    setSelectedDateFilter(filter)
    setCustomStartDate(startDate)
    setCustomEndDate(endDate)
    
    // Save to localStorage
    try {
      localStorage.setItem('all-orders-date-filter', filter)
    } catch (error) {
      console.warn('Could not save to localStorage:', error)
    }
  }

  const { data: ordersData, isLoading, error, refetch } = useQuery({
    queryKey: ['all-orders', sheetUrl, selectedDateFilter, customStartDate, customEndDate],
    queryFn: () => fetchAllOrders(sheetUrl, 5000, 0, undefined, selectedDateFilter, customStartDate, customEndDate), // Load all orders for infinite scroll
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

  // Debug logging
  console.log('AllOrders Debug:', {
    searchTerm,
    ordersData: ordersData ? {
      totalRecords: ordersData.total_records,
      ordersCount: ordersData.orders?.length,
      hasNext: ordersData.has_next
    } : null,
    isLoading,
    error: error?.message
  })

  if (!sheetUrl) {
    return (
      <div className="p-8">
        <div className="max-w-4xl mx-auto">
          <div className="bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-700 rounded-md p-4">
            <div className="flex">
              <ExclamationTriangleIcon className="h-5 w-5 text-warning-400" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-warning-800 dark:text-warning-200">
                  Google Sheet URL Required
                </h3>
                <p className="mt-1 text-sm text-warning-700 dark:text-warning-300">
                  Please go to Settings and enter your Google Sheets URL to view all orders.
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
              Loading All Orders
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
          <div className="bg-danger-50 dark:bg-danger-900/20 border border-danger-200 dark:border-danger-700 rounded-md p-4">
            <div className="flex">
              <ExclamationTriangleIcon className="h-5 w-5 text-danger-400" />
              <div className="mt-3">
                <h3 className="text-sm font-medium text-danger-800 dark:text-danger-200">
                  Error Loading Orders
                </h3>
                <p className="mt-1 text-sm text-danger-700 dark:text-danger-300">
                  Failed to load orders. Please check your Google Sheets URL and permissions.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!ordersData) return null

  // Filter orders based on search term
  const filteredOrders = ordersData.orders.filter((order: any) => {
    if (searchTerm === '') return true
    
    // More detailed search logging
    const searchLower = searchTerm.toLowerCase()
    const orderValues = Object.values(order)
    
    const hasMatch = orderValues.some(value => {
      const valueStr = String(value).toLowerCase()
      const matches = valueStr.includes(searchLower)
      
      // Log matches for debugging
      if (matches && searchTerm) {
        console.log('Found match:', {
          searchTerm,
          matchedValue: value,
          fieldName: Object.keys(order).find(key => order[key] === value)
        })
      }
      
      return matches
    })
    
    return hasMatch
  })

  // Log search results
  if (searchTerm) {
    console.log('Search Results:', {
      searchTerm,
      totalOrders: ordersData.orders.length,
      filteredCount: filteredOrders.length,
      firstFewResults: filteredOrders.slice(0, 3).map(order => ({
        product: order.Product,
        orderNumber: order['Order Number'],
        email: order.Email
      }))
    })
  }

  return (
    <div className="p-2 sm:p-4 lg:p-6 pb-20 lg:pb-8">
      <div className="max-w-full mx-auto px-2">
        {/* Header & Search */}
        <div className="relative mb-2">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between">
            <div className="flex-1">
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-gray-100">All Orders</h1>
              <p className="mt-0.5 text-xs text-gray-600 dark:text-gray-300">
                Browse and search through all orders.
              </p>
              
              {/* Date Filter */}
              <div className="mt-1.5">
                <DateFilter 
                  selectedFilter={selectedDateFilter}
                  onFilterChange={handleDateFilterChange}
                />
              </div>
              
              <div className="flex flex-wrap items-center gap-2 mt-1.5">
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {ordersData.total_records.toLocaleString()} orders
                  </div>
                  <div className="flex items-center space-x-1">
                    <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-success-500 live-indicator' : 'bg-gray-400'}`}></div>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {isConnected ? 'Live' : 'Cached'}
                    </span>
                  </div>
              </div>
            </div>
            
            {/* Desktop Search Bar - Always Visible */}
            <div className="hidden sm:block flex-shrink-0 mt-1 sm:mt-0 ml-4">
              <div className="relative max-w-xs w-full">
                <div className="absolute inset-y-0 left-0 pl-2 flex items-center pointer-events-none">
                  <MagnifyingGlassIcon className="h-4 w-4 text-gray-400" />
                </div>
                <input
                  type="text"
                  placeholder="Search orders..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="block w-full pl-8 pr-2 py-1.5 border border-gray-300 rounded-md leading-5 bg-white dark:bg-gray-800 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-primary-500 focus:border-primary-500 text-xs"
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

        {/* Search feedback */}
        {searchTerm && (
            <div className="mb-2 flex justify-end">
                <div className="text-xs text-gray-600 dark:text-gray-300">
                    Found {filteredOrders.length} matching orders
                </div>
            </div>
        )}


        {/* Mobile Cards or Desktop Table */}
        {filteredOrders.length > 0 ? (
          <>
            {isMobile ? (
              // Mobile Card View
              <div className="space-y-4">
                {filteredOrders.map((order: any, index: number) => (
                  <MobileOrderCard
                    key={order['Order Number'] || index}
                    order={order}
                    onEdit={(column, value) => {
                      // Handle cell edit
                      // This will be handled by the WebSocket connection
                      console.log('Edit:', { column, value, order })
                    }}
                  />
                ))}
              </div>
            ) : (
              // Desktop Table View with infinite scroll
              <EditableOrderTable 
                orders={filteredOrders} 
                sheetUrl={sheetUrl}
                onDataChange={() => refetch()}
                disablePagination={!!searchTerm}
              />
            )}
          </>
        ) : (
          <div className="card text-center py-12">
            <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-semibold text-gray-900">No orders found</h3>
            <p className="mt-1 text-sm text-gray-500">
              {searchTerm 
                ? 'Try adjusting your search criteria.'
                : 'No orders available in the system.'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
