import { ReactNode, useState } from 'react'

interface KPICardProps {
  title: string
  value: string | number
  icon: ReactNode
  color: 'primary' | 'success' | 'warning' | 'danger'
  highlight?: boolean
  percentageChange?: number
  percentageLeftMargin?: string
}

const colorClasses = {
  primary: {
    bg: 'bg-blue-50 dark:bg-blue-900/30',
    text: 'text-blue-600 dark:text-blue-300',
    border: 'border-blue-200 dark:border-blue-700'
  },
  success: {
    bg: 'bg-emerald-50 dark:bg-emerald-900/30',
    text: 'text-emerald-600 dark:text-emerald-300',
    border: 'border-emerald-200 dark:border-emerald-700'
  },
  warning: {
    bg: 'bg-amber-50 dark:bg-amber-900/30',
    text: 'text-amber-600 dark:text-amber-300',
    border: 'border-amber-200 dark:border-amber-700'
  },
  danger: {
    bg: 'bg-red-50 dark:bg-red-900/30',
    text: 'text-red-600 dark:text-red-300',
    border: 'border-red-200 dark:border-red-700'
  }
}

// Helper function to determine percentage color based on metric type
const getPercentageColor = (percentageChange: number, title: string): string => {
  const lowerTitle = title.toLowerCase()
  
  // Metrics where higher percentages are BAD (red for increases)
  const badMetrics = ['missing', 'error', 'failed', 'rejected', 'cancelled', 'returned']
  const isBadMetric = badMetrics.some(bad => lowerTitle.includes(bad))
  
  if (isBadMetric) {
    return percentageChange > 0 ? 'text-red-600 dark:text-red-400' : 
           percentageChange < 0 ? 'text-green-600 dark:text-green-400' : 
           'text-gray-500 dark:text-gray-400'
  }
  
  // For all other metrics, higher percentages are good (green)
  return percentageChange > 0 ? 'text-green-600 dark:text-green-400' : 
         percentageChange < 0 ? 'text-red-600 dark:text-red-400' : 
         'text-gray-500 dark:text-gray-400'
}

// Helper function to determine percentage arrow based on metric type
const getPercentageArrow = (percentageChange: number, title: string): string => {
  const lowerTitle = title.toLowerCase()
  
  // Metrics where higher percentages are BAD
  const badMetrics = ['missing', 'error', 'failed', 'rejected', 'cancelled', 'returned']
  const isBadMetric = badMetrics.some(bad => lowerTitle.includes(bad))
  
  if (isBadMetric) {
    return percentageChange > 0 ? '↗' : percentageChange < 0 ? '↘' : '→'
  }
  
  // For all other metrics, higher percentages are good
  return percentageChange > 0 ? '↗' : percentageChange < 0 ? '↘' : '→'
}

export default function KPICard({ title, value, icon, color, percentageChange }: KPICardProps) {
  const classes = colorClasses[color]
  
  // Create a unique key for this card's hidden state
  const cardKey = `kpi-hidden-${title.toLowerCase().replace(/\s+/g, '-')}`
  
  // Get hidden state from localStorage with fallback to false
  const [isHidden, setIsHidden] = useState(() => {
    try {
      return localStorage.getItem(cardKey) === 'true'
    } catch {
      return false
    }
  })
  

  
  // Toggle hidden state and save to localStorage
  const toggleHidden = () => {
    const newHidden = !isHidden
    setIsHidden(newHidden)
    try {
      localStorage.setItem(cardKey, newHidden.toString())
    } catch (error) {
      console.warn('Could not save to localStorage:', error)
    }
  }
  
  // Display value or asterisks with animation
  const displayValue = isHidden ? '****' : value
  
  return (
    <div className="card rounded-2xl shadow-lg hover:shadow-xl transition-shadow duration-200">
      <div className="flex flex-col p-0">
        <div className="flex items-start">
          {/* Fixed size icon container with perfect centering */}
          <div className={`flex-shrink-0 w-10 h-10 rounded-xl ${classes.bg} ${classes.border} border flex items-center justify-center shadow-md`}>
            <div className="flex items-center justify-center w-full h-full">
              {icon}
            </div>
          </div>
          <div className="ml-2 min-w-0 flex-1">
            <p className="text-xs font-medium text-gray-600 dark:text-gray-300 mb-0 truncate">{title}</p>
            <div 
              className={`font-bold text-lg sm:text-xl leading-tight cursor-pointer select-none transition-all duration-300 ease-in-out ${isHidden ? 'opacity-70 scale-95' : 'opacity-100 scale-100'}`}
              onClick={toggleHidden}
              title={isHidden ? 'Tap to show value' : 'Tap to hide value'}
            >
              <span 
                key={isHidden ? 'hidden' : 'visible'}
                className={`inline-block transition-all duration-300 ease-in-out animate-fade-in ${classes.text}`}
              >
                {displayValue}
              </span>
            </div>
          </div>
        </div>
        {percentageChange !== undefined && parseFloat(value.toString().replace(/[$,]/g, '')) >= 1 && (
          <div className={`text-xs font-medium mt-2 ml-0 ${
            getPercentageColor(percentageChange, title)
          }`}>
            {getPercentageArrow(percentageChange, title)} {Math.abs(percentageChange).toFixed(1)}% vs prev month
          </div>
        )}
      </div>
    </div>
  )
}
