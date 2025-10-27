import { ChartBarIcon } from '@heroicons/react/24/outline'

export default function Analytics() {
  return (
    <div className="min-h-screen bg-gray-50 w-full">
      <div className="max-w-full px-4 py-6 sm:px-6 lg:px-8 mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
          <p className="mt-1 text-sm text-gray-600">
            View order statistics and performance metrics
          </p>
        </div>

        {/* Coming Soon */}
        <div className="bg-white shadow-sm rounded-lg p-12 text-center">
          <ChartBarIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">Analytics Coming Soon</h3>
          <p className="mt-2 text-sm text-gray-500">
            Dashboard with charts, graphs, and detailed order analytics
          </p>
          <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-xs text-gray-500">Feature</p>
              <p className="text-sm font-medium text-gray-900 mt-1">Revenue Tracking</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-xs text-gray-500">Feature</p>
              <p className="text-sm font-medium text-gray-900 mt-1">Order Trends</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-xs text-gray-500">Feature</p>
              <p className="text-sm font-medium text-gray-900 mt-1">Performance Metrics</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

