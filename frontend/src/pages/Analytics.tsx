import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import {
  ShoppingCartIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  CurrencyDollarIcon,
  ArrowPathIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline'
import { fetchOrdersOverview } from '../services/api'
import KPICard from '../components/KPICard'
import TopProducts from '../components/TopProducts'
import DateFilter, { DateFilterOption } from '../components/DateFilter'

interface AnalyticsProps {
  sheetUrl: string
}

export default function Analytics({ sheetUrl }: AnalyticsProps) {
  const [selectedDateFilter, setSelectedDateFilter] = useState<DateFilterOption>(() => {
    // Try to get from localStorage first, fallback to all_time
    try {
      const saved = localStorage.getItem('analytics-selected-date-filter')
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

  const handleDateFilterChange = (filter: DateFilterOption, startDate?: string, endDate?: string) => {
    setSelectedDateFilter(filter)
    setCustomStartDate(startDate)
    setCustomEndDate(endDate)

    try {
      localStorage.setItem('analytics-selected-date-filter', filter)
      if (startDate) localStorage.setItem('analytics-custom-start-date', startDate)
      if (endDate) localStorage.setItem('analytics-custom-end-date', endDate)
    } catch (error) {
      console.warn('Could not save to localStorage:', error)
    }
  }

  // Construct query based on date filter (same logic as Dashboard)
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

  const { data: overview, isLoading, error, refetch } = useQuery({
    queryKey: ['orders-overview', sheetUrl, selectedDateFilter, customStartDate, customEndDate],
    queryFn: () => {
      const params = getDateRangeParams()
      return fetchOrdersOverview(sheetUrl, params)
    },
    enabled: !!sheetUrl,
  })

  const handleRefresh = () => {
    refetch()
  }

  // Debug logging to help identify data issues
  console.log('🔍 Analytics Debug - Data State:', {
    isLoading,
    hasOverview: !!overview,
    hasOverviewData: !!overview?.overview,
    selectedDateFilter,
    customStartDate,
    customEndDate,
    overviewKeys: overview?.overview ? Object.keys(overview.overview) : [],
    currentMonthOrders: overview?.overview?.current_month_orders,
    currentMonthShipped: overview?.overview?.current_month_shipped,
    currentMonthProfit: overview?.overview?.current_month_profit,
    error: error?.message
  })

  // Calculate percentage changes with improved logic
  const calculatePercentageChange = (current: number, previous: number): number => {
    // Handle edge cases
    if (previous === 0) {
      return current > 0 ? 100 : 0
    }
    if (current === 0 && previous > 0) {
      return -100
    }
    
    const change = ((current - previous) / previous) * 100
    return Math.round(change * 10) / 10 // Round to 1 decimal place
  }

  const getPercentageChange = (current: number, previous: number, metricName: string) => {
    // Only show percentage if we have meaningful data
    if (current === 0 && previous === 0) return undefined
    
    const change = calculatePercentageChange(current, previous)
    
    // Enhanced logging for debugging
    console.log(`${metricName} percentage change:`, {
      current,
      previous,
      change: `${change}%`,
      direction: change > 0 ? 'increase' : change < 0 ? 'decrease' : 'no change'
    })
    
    return change
  }

  if (isLoading) {
    return (
      <div className="p-4 sm:p-6 lg:p-8">
        <div className="max-w-6xl mx-auto">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4"></div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !overview || !overview.overview) {
    return (
      <div className="p-4 sm:p-6 lg:p-8">
        <div className="max-w-6xl mx-auto text-center">
          <div className="text-red-500 dark:text-red-400 mb-4">
            Failed to load analytics data. Please try again.
          </div>
          {error && (
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Error: {error.message || 'Unknown error occurred'}
            </div>
          )}
          {overview && (overview as any).error && (
            <div className="text-sm text-gray-600 dark:text-gray-400">
              API Error: {(overview as any).error}
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header with Date Picker */}
        <div className="mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Analytics</h1>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                Detailed performance metrics and insights
              </p>
            </div>
            
            {/* Date Filter and Refresh - Top Right on Desktop, Below Title on Mobile */}
            <div className="flex items-center space-x-3">
              <div className="w-48">
                <DateFilter
                  selectedFilter={selectedDateFilter}
                  onFilterChange={handleDateFilterChange}
                />
              </div>
              <button
                onClick={handleRefresh}
                disabled={isLoading}
                className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-600 focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center h-9"
                title="Refresh analytics data"
              >
                <ArrowPathIcon className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>



        {/* Month Performance */}
        <div className="mb-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
            <KPICard
              title="Orders"
              value={(overview?.overview?.current_month_orders || 0).toLocaleString()}
              icon={<ShoppingCartIcon className="h-6 w-6 text-blue-500 dark:text-blue-300" />}
              color="primary"
              percentageChange={getPercentageChange(
                overview?.overview?.current_month_orders || 0,
                overview?.overview?.previous_month_orders || 0,
                'Orders'
              )}

            />
            <KPICard
              title="Shipped"
              value={(overview?.overview?.current_month_shipped || 0).toLocaleString()}
              icon={<CheckCircleIcon className="h-6 w-6 text-emerald-500 dark:text-emerald-300" />}
              color="success"
              percentageChange={getPercentageChange(
                overview?.overview?.current_month_shipped || 0,
                overview?.overview?.previous_month_shipped || 0,
                'Shipped'
              )}

            />
            <KPICard
              title="Scanned"
              value={(overview?.overview?.current_month_packages_scanned || 0).toLocaleString()}
              icon={<CheckCircleIcon className="h-6 w-6 text-indigo-500 dark:text-blue-300" />}
              color="primary"
              percentageChange={getPercentageChange(
                overview?.overview?.current_month_packages_scanned || 0,
                overview?.overview?.previous_month_packages_scanned || 0,
                'Packages Scanned'
              )}

            />
            <KPICard
              title="Missing"
              value={(overview?.overview?.current_month_missing_packages || 0).toLocaleString()}
              icon={<ExclamationTriangleIcon className="h-6 w-6 text-amber-500 dark:text-amber-300" />}
              color="warning"
              percentageChange={getPercentageChange(
                overview?.overview?.current_month_missing_packages || 0,
                overview?.overview?.previous_month_missing_packages || 0,
                'Missing Packages'
              )}

            />
            <KPICard
              title="Profit"
              value={overview?.overview?.current_month_profit || "$0.00"}
              icon={<CurrencyDollarIcon className="h-6 w-6 text-emerald-500 dark:text-emerald-300" />}
              color="success"
              percentageChange={getPercentageChange(
                parseFloat((overview?.overview?.current_month_profit || "$0.00").replace(/[$,]/g, '')),
                parseFloat((overview?.overview?.previous_month_profit || "$0.00").replace(/[$,]/g, '')),
                'Profit'
              )}

            />
          </div>
        </div>

        {/* Top Products Section */}
        <div className="mb-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <TopProducts
              topProducts={overview?.top_products || {}}
              detailedProducts={overview?.detailed_products || {}}
              title="Top Products by Orders"
              maxItems={5}
            />
            
            {/* Placeholder for future analytics components */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6">
              <div className="flex items-center mb-4">
                <ChartBarIcon className="h-6 w-6 text-blue-500 dark:text-blue-300 mr-2" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Performance Insights</h3>
              </div>
              <div className="text-center py-8">
                <div className="text-gray-400 dark:text-gray-600 mb-2">
                  <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <p className="text-gray-500 dark:text-gray-400">More analytics coming soon</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
