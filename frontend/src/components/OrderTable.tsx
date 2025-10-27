import { useState } from 'react'
import { 
  ChevronLeftIcon, 
  ChevronRightIcon,
  ArrowUpIcon,
  ArrowDownIcon
} from '@heroicons/react/24/outline'

interface Order {
  Date: string
  Time: string
  Product: string
  Price: string
  Total: string
  Commission: string
  Quantity: number
  Profile: string
  'Proxy List': string
  'Order Number': string
  Email: string
  'Reference #': string
  'Posted Date': string
  'Tracking Number': string
  Status: string
  'QTY Received': number
  'Order ID': string
  Created: string
  Modified: string
}

interface OrderTableProps {
  orders: Order[]
  showPendingHighlight?: boolean
}

export default function OrderTable({ orders, showPendingHighlight = false }: OrderTableProps) {
  const [currentPage, setCurrentPage] = useState(1)
  const [sortField, setSortField] = useState<keyof Order>('Date')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const itemsPerPage = 25

  // Sort orders
  const sortedOrders = [...orders].sort((a, b) => {
    let aValue = a[sortField]
    let bValue = b[sortField]
    
    // Handle different data types
    if (sortField === 'Date' || sortField === 'Posted Date') {
      aValue = new Date(aValue).getTime()
      bValue = new Date(bValue).getTime()
    } else if (typeof aValue === 'string') {
      aValue = aValue.toLowerCase()
      bValue = bValue.toLowerCase()
    }
    
    if (sortDirection === 'asc') {
      return aValue > bValue ? 1 : -1
    } else {
      return aValue < bValue ? 1 : -1
    }
  })

  // Pagination
  const totalPages = Math.ceil(sortedOrders.length / itemsPerPage)
  const startIndex = (currentPage - 1) * itemsPerPage
  const paginatedOrders = sortedOrders.slice(startIndex, startIndex + itemsPerPage)

  const handleSort = (field: keyof Order) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const getStatusBadge = (status: string) => {
    const statusLower = status.toLowerCase()
    if (statusLower === 'verified') {
      return <span className="px-2 py-1 text-xs font-semibold rounded-full status-verified">Verified</span>
    } else if (statusLower === 'cancelled') {
      return <span className="px-2 py-1 text-xs font-semibold rounded-full status-cancelled">Cancelled</span>
    } else {
      return <span className="px-2 py-1 text-xs font-semibold rounded-full status-unverified">Unverified</span>
    }
  }

  const isPendingOrder = (order: Order) => {
    return (
      order.Status?.toUpperCase() !== 'VERIFIED' ||
      !order['Tracking Number'] ||
      order['QTY Received'] < order.Quantity
    )
  }

  const SortIcon = ({ field }: { field: keyof Order }) => {
    if (sortField !== field) return null
    return sortDirection === 'asc' ? (
      <ArrowUpIcon className="h-4 w-4" />
    ) : (
      <ArrowDownIcon className="h-4 w-4" />
    )
  }

  return (
    <div className="card">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {[
                { key: 'Date', label: 'Date' },
                { key: 'Product', label: 'Product' },
                { key: 'Price', label: 'Price' },
                { key: 'Quantity', label: 'Qty' },
                { key: 'QTY Received', label: 'Received' },
                { key: 'Status', label: 'Status' },
                { key: 'Tracking Number', label: 'Tracking' },
                { key: 'Order Number', label: 'Order #' },
                { key: 'Profile', label: 'Profile' }
              ].map(({ key, label }) => (
                <th
                  key={key}
                  onClick={() => handleSort(key as keyof Order)}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                >
                  <div className="flex items-center space-x-1">
                    <span>{label}</span>
                    <SortIcon field={key as keyof Order} />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {paginatedOrders.map((order, index) => (
              <tr 
                key={index} 
                className={`hover:bg-gray-50 ${
                  showPendingHighlight && isPendingOrder(order) ? 'bg-warning-50 border-l-4 border-l-warning-400' : ''
                }`}
              >
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {order.Date ? new Date(order.Date).toLocaleDateString() : '-'}
                </td>
                <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate" title={order.Product}>
                  {order.Product || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {order.Price || '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-center">
                  {order.Quantity || 0}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-center">
                  <span className={
                    order['QTY Received'] < order.Quantity 
                      ? 'text-warning-600 font-semibold' 
                      : 'text-success-600'
                  }>
                    {order['QTY Received'] || 0}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getStatusBadge(order.Status || 'Unverified')}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {order['Tracking Number'] ? (
                    <span className="text-primary-600 font-medium">
                      {order['Tracking Number']}
                    </span>
                  ) : (
                    <span className="text-gray-400">No tracking</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {order['Order Number'] || '-'}
                </td>
                <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate" title={order.Profile}>
                  {order.Profile || '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-6 py-3 border-t border-gray-200">
          <div className="flex-1 flex justify-between sm:hidden">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1}
              className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages}
              className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
          <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
            <div>
              <p className="text-sm text-gray-700">
                Showing <span className="font-medium">{startIndex + 1}</span> to{' '}
                <span className="font-medium">
                  {Math.min(startIndex + itemsPerPage, sortedOrders.length)}
                </span>{' '}
                of <span className="font-medium">{sortedOrders.length}</span> results
              </p>
            </div>
            <div>
              <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                <button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeftIcon className="h-5 w-5" />
                </button>
                
                {/* Page numbers */}
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum
                  if (totalPages <= 5) {
                    pageNum = i + 1
                  } else if (currentPage <= 3) {
                    pageNum = i + 1
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i
                  } else {
                    pageNum = currentPage - 2 + i
                  }
                  
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setCurrentPage(pageNum)}
                      className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium ${
                        currentPage === pageNum
                          ? 'z-10 bg-primary-50 border-primary-500 text-primary-600'
                          : 'bg-white border-gray-300 text-gray-500 hover:bg-gray-50'
                      }`}
                    >
                      {pageNum}
                    </button>
                  )
                })}
                
                <button
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage === totalPages}
                  className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRightIcon className="h-5 w-5" />
                </button>
              </nav>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
