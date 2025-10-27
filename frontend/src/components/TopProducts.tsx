import { ReactNode } from 'react'
import { TrophyIcon, ChartBarIcon, CurrencyDollarIcon, ShoppingBagIcon, TruckIcon, CheckCircleIcon } from '@heroicons/react/24/outline'
import { DetailedProduct } from '../services/api'

interface TopProductsProps {
  topProducts: Record<string, number>
  detailedProducts?: Record<string, DetailedProduct>
  title?: string
  maxItems?: number
}

export default function TopProducts({ 
  topProducts, 
  detailedProducts, 
  title = "Top Products", 
  maxItems = 5 
}: TopProductsProps) {
  // Convert the object to an array and sort by count (descending)
  const productsArray = Object.entries(topProducts)
    .map(([product, count]) => ({ 
      product, 
      count,
      details: detailedProducts?.[product]
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, maxItems)

  if (productsArray.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6">
        <div className="flex items-center mb-4">
          <TrophyIcon className="h-6 w-6 text-amber-500 dark:text-amber-300 mr-2" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
        </div>
        <div className="text-center py-8">
          <ChartBarIcon className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-gray-400">No product data available</p>
        </div>
      </div>
    )
  }

  const maxCount = productsArray[0]?.count || 1

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg p-6">
      <div className="flex items-center mb-4">
        <TrophyIcon className="h-6 w-6 text-amber-500 dark:text-amber-300 mr-2" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
      </div>
      
      <div className="space-y-3">
        {productsArray.map((item, index) => {
          const percentage = (item.count / maxCount) * 100
          const rank = index + 1
          
          // Different colors for top 3
          let rankColor = 'text-gray-500 dark:text-gray-400'
          let bgColor = 'bg-gray-100 dark:bg-gray-700'
          
          if (rank === 1) {
            rankColor = 'text-amber-600 dark:text-amber-400'
            bgColor = 'bg-amber-50 dark:bg-amber-900/30'
          } else if (rank === 2) {
            rankColor = 'text-gray-600 dark:text-gray-300'
            bgColor = 'bg-gray-50 dark:bg-gray-700/50'
          } else if (rank === 3) {
            rankColor = 'text-amber-700 dark:text-amber-500'
            bgColor = 'bg-amber-50/50 dark:bg-amber-900/20'
          }

          return (
            <div key={item.product} className="space-y-3">
              {/* Main Product Row */}
              <div className="flex items-center space-x-3">
                {/* Rank */}
                <div className={`flex-shrink-0 w-8 h-8 rounded-full ${bgColor} flex items-center justify-center`}>
                  <span className={`text-sm font-bold ${rankColor}`}>
                    {rank}
                  </span>
                </div>
                
                {/* Product Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                      {item.product}
                    </p>
                    <p className="text-sm font-semibold text-gray-600 dark:text-gray-300">
                      {item.count.toLocaleString()} orders
                    </p>
                  </div>
                  
                  {/* Progress Bar */}
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full transition-all duration-300 ${
                        rank === 1 ? 'bg-gradient-to-r from-amber-400 to-amber-500' :
                        rank === 2 ? 'bg-gradient-to-r from-gray-400 to-gray-500' :
                        rank === 3 ? 'bg-gradient-to-r from-amber-500 to-amber-600' :
                        'bg-gradient-to-r from-blue-400 to-blue-500'
                      }`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              </div>
              
              {/* Detailed Metrics */}
              {item.details && (
                <div className="ml-11 grid grid-cols-2 gap-3 text-xs">
                  {/* Revenue & Profit */}
                  <div className="flex items-center space-x-2">
                    <CurrencyDollarIcon className="h-4 w-4 text-green-500" />
                    <span className="text-gray-600 dark:text-gray-400">
                      Revenue: <span className="font-medium text-gray-900 dark:text-gray-100">
                        ${item.details.total_revenue.toLocaleString()}
                      </span>
                    </span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <CurrencyDollarIcon className="h-4 w-4 text-blue-500" />
                    <span className="text-gray-600 dark:text-gray-400">
                      Profit: <span className="font-medium text-gray-900 dark:text-gray-100">
                        ${item.details.total_profit.toLocaleString()}
                      </span>
                    </span>
                  </div>
                  
                  {/* Quantity & Shipped */}
                  <div className="flex items-center space-x-2">
                    <ShoppingBagIcon className="h-4 w-4 text-purple-500" />
                    <span className="text-gray-600 dark:text-gray-400">
                      Qty: <span className="font-medium text-gray-900 dark:text-gray-100">
                        {item.details.total_quantity.toLocaleString()}
                      </span>
                    </span>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <TruckIcon className="h-4 w-4 text-indigo-500" />
                    <span className="text-gray-600 dark:text-gray-400">
                      Shipped: <span className="font-medium text-gray-900 dark:text-gray-100">
                        {item.details.shipped_count.toLocaleString()}
                      </span>
                    </span>
                  </div>
                  
                  {/* Fulfillment Rate */}
                  <div className="col-span-2 flex items-center space-x-2">
                    <CheckCircleIcon className="h-4 w-4 text-emerald-500" />
                    <span className="text-gray-600 dark:text-gray-400">
                      Fulfillment Rate: <span className="font-medium text-gray-900 dark:text-gray-100">
                        {item.details.fulfillment_rate.toFixed(1)}%
                      </span>
                    </span>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
      
      {productsArray.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
            Showing top {productsArray.length} products by order count
          </p>
        </div>
      )}
    </div>
  )
}
