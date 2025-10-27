import { useQuery } from '@tanstack/react-query'
import { Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, ComposedChart } from 'recharts'
import { fetchMonthlyRevenue } from '../services/api'

interface MonthlyRevenueChartProps {
  sheetUrl: string
}

export default function MonthlyRevenueChart({ sheetUrl }: MonthlyRevenueChartProps) {
  const { data: revenueData, isLoading, error } = useQuery({
    queryKey: ['monthly-revenue', sheetUrl],
    queryFn: () => fetchMonthlyRevenue(sheetUrl),
    enabled: !!sheetUrl,
    staleTime: 1000 * 60 * 60 * 24, // 24 hours for past months
    refetchInterval: (data) => {
      if (!data || !data.monthly_data) return false
      
      const now = new Date()
      const currentMonth = now.getMonth()
      const currentYear = now.getFullYear()
      
      // Check if we have current month data
      const hasCurrentMonth = data.monthly_data.some(item => 
        item.year === currentYear && item.month_num === currentMonth + 1
      )
      
      // Check if we have previous month data
      const hasPreviousMonth = data.monthly_data.some(item => {
        if (currentMonth === 0) {
          return item.year === currentYear - 1 && item.month_num === 12
        } else {
          return item.year === currentYear && item.month_num === currentMonth
        }
      })
      
      // If we have current or previous month data, refresh every time
      if (hasCurrentMonth || hasPreviousMonth) {
        return false // Let React Query handle refetching on page load
      }
      
      // For older months, refresh once per day
      return 1000 * 60 * 60 * 24
    }
  })

  if (isLoading) {
    return (
      <div className="h-48 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error || !revenueData) {
    return (
      <div className="h-48 flex items-center justify-center text-red-500 dark:text-red-400">
        Failed to load revenue data
      </div>
    )
  }

  if (!revenueData.monthly_data || revenueData.monthly_data.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center text-gray-500 dark:text-gray-400">
        No revenue data available
      </div>
    )
  }

  // Format the data for the chart
  const chartData = revenueData.monthly_data.map(item => ({
    month: item.month,
    revenue: item.revenue,
    formattedRevenue: `$${item.revenue.toLocaleString()}`
  }))
  
  // Debug logging
  console.log('Monthly Revenue Data:', revenueData.monthly_data)
  console.log('Chart Data:', chartData)

  return (
    <div className="h-64">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Monthly Revenue Trend</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">Revenue by month from January 2025</p>
      </div>
      
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 20, right: 10, left: 0, bottom: 50 }}>
          {/* Gradients for styling */}
          <defs>
            <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3B82F6" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#1D4ED8" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id="lineGradient" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#3B82F6" stopOpacity={1} />
              <stop offset="100%" stopColor="#1D4ED8" stopOpacity={0.8} />
            </linearGradient>
          </defs>
          
          <CartesianGrid strokeDasharray="3 3" stroke="#9CA3AF" strokeOpacity={0.3} className="dark:opacity-20" />
          <XAxis 
            dataKey="month" 
            stroke="#6B7280"
            className="dark:stroke-gray-400"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value) => {
              const [year, month] = value.split('-')
              const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
              return monthNames[parseInt(month) - 1]
            }}
          />
          <YAxis 
            stroke="#6B7280"
            className="dark:stroke-gray-400"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
          />
          <Tooltip 
            contentStyle={{
              backgroundColor: '#1F2937',
              border: '1px solid #374151',
              borderRadius: '8px',
              color: '#F9FAFB',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
              fontSize: '13px',
              padding: '8px 12px'
            }}
            formatter={(value: number) => [`$${value.toLocaleString()}`, 'Revenue']}
            labelFormatter={(label) => {
              const [year, month] = label.split('-')
              const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 
                                'July', 'August', 'September', 'October', 'November', 'December']
              return `${monthNames[parseInt(month) - 1]} ${year}`
            }}
          />
          
          {/* Area fill under the line */}
          <Area 
            type="monotone"
            dataKey="revenue"
            fill="url(#areaGradient)"
            stroke="none"
          />
          
          {/* Line on top */}
          <Line 
            type="monotone"
            dataKey="revenue" 
            stroke="#3B82F6"
            strokeWidth={3}
            dot={{ fill: '#3B82F6', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6, fill: '#1D4ED8', strokeWidth: 2 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
