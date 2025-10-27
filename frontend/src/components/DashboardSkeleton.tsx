import React from 'react'

export default function DashboardSkeleton() {
  return (
    <div className="p-4 sm:p-6 lg:p-8 pb-20 lg:pb-8 animate-pulse">
      <div className="max-w-7xl mx-auto">
        {/* Header Skeleton */}
        <div className="mb-6 lg:mb-8">
          <div className="h-7 sm:h-9 bg-gray-200 dark:bg-gray-700 rounded w-64 sm:w-96 mb-4"></div>
          <div className="h-4 sm:h-5 bg-gray-200 dark:bg-gray-700 rounded w-60 sm:w-80 mb-2"></div>
          <div className="h-3 sm:h-4 bg-gray-200 dark:bg-gray-700 rounded w-48 sm:w-64"></div>
        </div>

        {/* Today's Performance Skeleton */}
        <div className="mb-6">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-48 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="card">
                <div className="flex items-center">
                  <div className="w-12 h-12 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
                  <div className="ml-4 flex-1">
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24 mb-2"></div>
                    <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Overall Stats Skeleton */}
        <div className="mb-8">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-32 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="card">
                <div className="flex items-center">
                  <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
                  <div className="ml-4 flex-1">
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-28 mb-2"></div>
                    <div className="h-7 bg-gray-200 dark:bg-gray-700 rounded w-24"></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Inventory Status Cards Skeleton */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card">
              <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-32 mb-4"></div>
              <div className="space-y-3">
                {[1, 2, 3].map((j) => (
                  <div key={j} className="flex justify-between items-center">
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24"></div>
                    <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-16"></div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Charts Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {[1, 2].map((i) => (
            <div key={i} className="card">
              <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-48 mb-4"></div>
              <div className="h-80 bg-gray-200 dark:bg-gray-700 rounded"></div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
