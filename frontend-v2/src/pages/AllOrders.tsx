import { useQuery } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import {
  MagnifyingGlassIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'
import { fetchOrders, Order } from '../services/api'
import { useWebSocket } from '../hooks/useWebSocket'

// Loading messages that cycle through
const LOADING_MESSAGES = [
  "Loading orders from database...",
  "Processing order data...",
  "Analyzing order details...",
  "Preparing order table...",
  "Syncing with SQLite...",
  "Almost ready..."
]

export default function AllOrders() {
  const [searchTerm, setSearchTerm] = useState('')
  const [loadingMessage, setLoadingMessage] = useState(LOADING_MESSAGES[0])
  const [loadingProgress, setLoadingProgress] = useState(0)
  const [page, setPage] = useState(1)
  const [selectedStatus, setSelectedStatus] = useState<string | undefined>()

  // Enable real-time updates via WebSocket
  const { isConnected } = useWebSocket((message) => {
    // Handle new order messages
    if (message.type === 'new_order') {
      console.log('📦 New order received:', message.order)
      refetch()
    }
  })

  const { data: ordersData, isLoading, error, refetch } = useQuery({
    queryKey: ['orders-v2', page, selectedStatus, searchTerm],
    queryFn: () => fetchOrders(page, 100, selectedStatus, searchTerm),
    refetchInterval: 5000, // Auto-refresh every 5 seconds
  })

  // Progress bar and loading message animation
  useEffect(() => {
    if (isLoading) {
      let progress = 0
      let messageIndex = 0

      const progressInterval = setInterval(() => {
        progress += Math.random() * 15 + 5
        if (progress >= 90) progress = 90
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

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-gray-50">
        <div className="max-w-md w-full text-center">
          {/* Progress Bar */}
          <div className="mb-6">
            <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
              <div
                className="bg-blue-600 h-3 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${loadingProgress}%` }}
              ></div>
            </div>
            <div className="text-sm text-gray-500">
              {Math.round(loadingProgress)}% Complete
            </div>
          </div>

          {/* Loading Message */}
          <div className="mb-8">
            <div className="text-lg font-medium text-gray-900 mb-2">
              Loading Orders
            </div>
            <div className="text-sm text-gray-600">
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
      <div className="p-8 bg-gray-50 min-h-screen">
        <div className="max-w-4xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">
                  Error Loading Orders
                </h3>
                <p className="mt-1 text-sm text-red-700">
                  {error instanceof Error ? error.message : 'Failed to load orders. Please check your connection.'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!ordersData) return null

  const orders = ordersData.orders

  return (
    <div className="min-h-screen bg-gray-50 w-full">
      <div className="max-w-full px-4 py-6 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">All Orders</h1>
              <p className="mt-1 text-sm text-gray-600">
                Real-time view of all orders from webhooks
              </p>
              <div className="flex items-center gap-4 mt-2">
                <div className="text-sm text-gray-500">
                  {ordersData.total.toLocaleString()} total orders
                </div>
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`}></div>
                  <span className="text-sm text-gray-500">
                    {isConnected ? 'Live' : 'Disconnected'}
                  </span>
                </div>
                <div className="flex items-center space-x-1 text-xs text-gray-400">
                  <ArrowPathIcon className="h-3 w-3 animate-spin" />
                  <span>Auto-refresh: 5s</span>
                </div>
              </div>
            </div>

            {/* Refresh Button */}
            <button
              onClick={() => refetch()}
              className="mt-4 sm:mt-0 inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <ArrowPathIcon className="h-4 w-4 mr-2" />
              Refresh
            </button>
          </div>
        </div>

        {/* Search & Filters */}
        <div className="mb-6 flex flex-col sm:flex-row gap-4">
          {/* Search */}
          <div className="flex-1">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                placeholder="Search by order number, product, email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Status Filter */}
          <div>
            <select
              value={selectedStatus || ''}
              onChange={(e) => setSelectedStatus(e.target.value || undefined)}
              className="block w-full sm:w-48 px-3 py-2 border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Statuses</option>
              <option value="PENDING">Pending</option>
              <option value="VERIFIED">Verified</option>
              <option value="PROCESSING">Processing</option>
              <option value="SHIPPED">Shipped</option>
              <option value="DELIVERED">Delivered</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </div>
        </div>

        {/* Orders Table - Compact with All Columns */}
        {orders.length > 0 ? (
          <div className="bg-white shadow-sm rounded-lg overflow-hidden w-full">
            <div className="overflow-x-auto w-full">
              <table className="divide-y divide-gray-200 text-xs" style={{ width: '100%', minWidth: '1400px' }}>
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Order #</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Comm.</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Qty</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Profile</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Proxy</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Ref #</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Tracking</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Source</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-100">
                  {orders.map((order: Order) => (
                    <tr key={order.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-3 py-1.5 whitespace-nowrap text-xs text-gray-900">
                        {order.order_date ? new Date(order.order_date).toLocaleDateString() : '-'}
                      </td>
                      <td className="px-3 py-1.5 whitespace-nowrap text-xs text-gray-500">
                        {order.order_time || '-'}
                      </td>
                      <td className="px-3 py-1.5 whitespace-nowrap text-xs font-medium text-gray-900">
                        {order.order_number}
                      </td>
                      <td className="px-3 py-1.5 text-xs text-gray-900 max-w-xs truncate" title={order.product || ''}>
                        {order.product || '-'}
                      </td>
                      <td className="px-3 py-1.5 whitespace-nowrap text-xs text-gray-900">
                        ${order.price?.toFixed(2) || '0.00'}
                      </td>
                      <td className="px-3 py-1.5 whitespace-nowrap text-xs text-gray-900">
                        {order.total ? `$${order.total.toFixed(2)}` : '-'}
                      </td>
                      <td className="px-3 py-1.5 whitespace-nowrap text-xs text-gray-900">
                        ${order.commission?.toFixed(2) || '0.00'}
                      </td>
                      <td className="px-3 py-1.5 whitespace-nowrap text-xs text-gray-900 text-center">
                        {order.quantity || 1}
                      </td>
                      <td className="px-3 py-1.5 text-xs text-gray-500 max-w-xs truncate" title={order.email || ''}>
                        {order.email || '-'}
                      </td>
                      <td className="px-3 py-1.5 text-xs text-gray-500 max-w-xs truncate" title={order.profile || ''}>
                        {order.profile || '-'}
                      </td>
                      <td className="px-3 py-1.5 text-xs text-gray-500 max-w-xs truncate" title={order.proxy_list || ''}>
                        {order.proxy_list || '-'}
                      </td>
                      <td className="px-3 py-1.5 whitespace-nowrap text-xs text-gray-500">
                        {order.reference_number || '-'}
                      </td>
                      <td className="px-3 py-1.5 whitespace-nowrap">
                        {order.status ? (
                          <span className={`inline-flex px-1.5 py-0.5 text-xs font-semibold rounded ${
                            order.status === 'VERIFIED' || order.status === 'verified' ? 'bg-green-100 text-green-800' :
                            order.status === 'PENDING' || order.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                            order.status === 'SHIPPED' || order.status === 'shipped' ? 'bg-blue-100 text-blue-800' :
                            order.status === 'CANCELLED' || order.status === 'cancelled' ? 'bg-red-100 text-red-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {order.status}
                          </span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-3 py-1.5 text-xs text-gray-500 max-w-xs truncate" title={order.tracking_number || ''}>
                        {order.tracking_number || '-'}
                      </td>
                      <td className="px-3 py-1.5 whitespace-nowrap text-xs text-gray-500">
                        <span className="inline-flex px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded">
                          {order.source}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
              <div className="flex-1 flex justify-between sm:hidden">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={!ordersData.has_previous}
                  className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={!ordersData.has_next}
                  className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
              <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-gray-700">
                    Showing page <span className="font-medium">{page}</span> of{' '}
                    <span className="font-medium">{Math.ceil(ordersData.total / 100)}</span>
                  </p>
                </div>
                <div>
                  <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={!ordersData.has_previous}
                      className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setPage(p => p + 1)}
                      disabled={!ordersData.has_next}
                      className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </nav>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-white shadow-sm rounded-lg p-12 text-center">
            <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-semibold text-gray-900">No orders found</h3>
            <p className="mt-1 text-sm text-gray-500">
              {searchTerm
                ? 'Try adjusting your search criteria.'
                : 'Orders will appear here as they come in via webhooks.'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

