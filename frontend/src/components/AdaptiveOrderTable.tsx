import { useState, useCallback } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  ChevronLeftIcon, 
  ChevronRightIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  PencilIcon,
  CheckIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'
import { updateCell } from '../services/api'
import toast from 'react-hot-toast'

interface Order {
  [key: string]: any // Allow any columns since we're adapting to user's structure
}

interface AdaptiveOrderTableProps {
  orders: Order[]
  sheetUrl: string
  showPendingHighlight?: boolean
  onDataChange?: () => void
}

interface EditingCell {
  rowId: string
  column: string
  value: string
}

export default function AdaptiveOrderTable({ 
  orders, 
  sheetUrl, 
  showPendingHighlight = false,
  onDataChange
}: AdaptiveOrderTableProps) {
  const [currentPage, setCurrentPage] = useState(1)
  const [sortField, setSortField] = useState<string>('Date')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [editingCell, setEditingCell] = useState<EditingCell | null>(null)
  const itemsPerPage = 25

  const queryClient = useQueryClient()

  // Mutation for updating cells
  const cellUpdateMutation = useMutation({
    mutationFn: ({ rowId, column, value }: { rowId: string, column: string, value: string }) =>
      updateCell(sheetUrl, { row_id: rowId, column, value }),
    onSuccess: () => {
      toast.success('Cell updated successfully!')
      queryClient.invalidateQueries({ queryKey: ['orders-overview'] })
      queryClient.invalidateQueries({ queryKey: ['pending-orders'] })
      queryClient.invalidateQueries({ queryKey: ['all-orders'] })
      onDataChange?.()
    },
    onError: (error: any) => {
      toast.error(`Failed to update cell: ${error.response?.data?.detail || error.message}`)
    }
  })

  // Get the columns from the first order (dynamic columns)
  const availableColumns = orders.length > 0 ? Object.keys(orders[0]).filter(key => key !== '_row_id') : []
  
  // Priority columns to show first (based on your data structure)
  const priorityColumns = ['Date', 'Item', 'Orders', 'Charged', 'Shipped', 'Scanned', 'Missing', 'Spend', 'Paid Out', 'PnL/BE']
  
  // Reorder columns to show priority ones first
  const displayColumns = [
    ...priorityColumns.filter(col => availableColumns.includes(col)),
    ...availableColumns.filter(col => !priorityColumns.includes(col))
  ].slice(0, 10) // Limit to 10 columns for better display

  // Editable columns - numeric and text fields that make sense to edit
  const editableColumns = [
    'Orders', 'Shipped', 'Scanned', 'Missing', 'Spend', 'Charged', 'Paid Out', 'PnL/BE'
  ]

  // Sort orders
  const sortedOrders = [...orders].sort((a, b) => {
    let aValue = a[sortField]
    let bValue = b[sortField]
    
    if (sortField === 'Date') {
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

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const handleCellEdit = useCallback((rowId: string, column: string, currentValue: string) => {
    if (!editableColumns.includes(column)) return
    
    setEditingCell({
      rowId,
      column,
      value: String(currentValue || '')
    })
  }, [])

  const handleSaveEdit = useCallback(() => {
    if (!editingCell) return

    cellUpdateMutation.mutate({
      rowId: editingCell.rowId,
      column: editingCell.column,
      value: editingCell.value
    })

    setEditingCell(null)
  }, [editingCell, cellUpdateMutation])

  const handleCancelEdit = useCallback(() => {
    setEditingCell(null)
  }, [])

  const isPendingOrder = (order: Order) => {
    // Based on your data: orders with Missing > 0 or Shipped < Orders
    const missing = Number(order.Missing || 0)
    const shipped = Number(order.Shipped || 0)
    const ordered = Number(order.Orders || 0)
    
    return missing > 0 || shipped < ordered
  }

  const SortIcon = ({ field }: { field: string }) => {
    if (sortField !== field) return null
    return sortDirection === 'asc' ? (
      <ArrowUpIcon className="h-4 w-4" />
    ) : (
      <ArrowDownIcon className="h-4 w-4" />
    )
  }

  const formatValue = (value: any, column: string) => {
    if (!value && value !== 0) return '-'
    
    // Format currency columns
    if (['Spend', 'Charged', 'Paid Out', 'PnL/BE'].includes(column)) {
      const num = Number(String(value).replace(/[$,]/g, ''))
      return isNaN(num) ? value : `$${num.toLocaleString()}`
    }
    
    // Format dates
    if (column === 'Date') {
      try {
        return new Date(value).toLocaleDateString()
      } catch {
        return value
      }
    }
    
    return value
  }

  const EditableCell = ({ 
    order, 
    column, 
    value, 
    isEditable 
  }: { 
    order: Order
    column: string
    value: any
    isEditable: boolean 
  }) => {
    const isEditing = editingCell?.rowId === order._row_id && editingCell?.column === column
    const displayValue = formatValue(value, column)

    if (isEditing) {
      return (
        <div className="flex items-center space-x-1">
          <input
            type="text"
            value={editingCell.value}
            onChange={(e) => setEditingCell({ ...editingCell, value: e.target.value })}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSaveEdit()
              if (e.key === 'Escape') handleCancelEdit()
            }}
            className="w-full px-2 py-1 text-sm border border-primary-300 rounded focus:outline-none focus:ring-1 focus:ring-primary-500"
            autoFocus
          />
          <button
            onClick={handleSaveEdit}
            className="p-1 text-success-600 hover:text-success-800"
            disabled={cellUpdateMutation.isPending}
          >
            <CheckIcon className="h-4 w-4" />
          </button>
          <button
            onClick={handleCancelEdit}
            className="p-1 text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="h-4 w-4" />
          </button>
        </div>
      )
    }

    return (
      <div 
        className={`group flex items-center justify-between ${
          isEditable ? 'cursor-pointer hover:bg-gray-50 px-2 py-1 rounded' : ''
        }`}
        onClick={() => isEditable && handleCellEdit(order._row_id!, column, String(value || ''))}
      >
        <span className="truncate" title={String(displayValue)}>
          {displayValue}
        </span>
        {isEditable && (
          <PencilIcon className="h-3 w-3 text-gray-400 opacity-0 group-hover:opacity-100 ml-1" />
        )}
      </div>
    )
  }

  if (orders.length === 0) {
    return (
      <div className="card text-center py-12">
        <div className="text-gray-400 text-lg mb-2">No orders found</div>
        <p className="text-gray-500">Your order data will appear here once connected to Google Sheets</p>
      </div>
    )
  }

  return (
    <div className="card">
      {/* Live editing indicator */}
      <div className="flex items-center justify-between mb-4 p-3 bg-primary-50 border border-primary-200 rounded-md">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-success-500 rounded-full live-indicator"></div>
          <span className="text-sm font-medium text-primary-800">
            Live editing enabled - Your actual sheet columns displayed
          </span>
        </div>
        <span className="text-xs text-primary-600">
          Showing {displayColumns.length} columns | {orders.length} total rows
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {displayColumns.map((column) => (
                <th
                  key={column}
                  onClick={() => handleSort(column)}
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                >
                  <div className="flex items-center space-x-1">
                    <span>{column}</span>
                    <SortIcon field={column} />
                    {editableColumns.includes(column) && (
                      <PencilIcon className="h-3 w-3 text-primary-400" />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {paginatedOrders.map((order, index) => (
              <tr 
                key={order._row_id || index} 
                className={`hover:bg-gray-50 ${
                  showPendingHighlight && isPendingOrder(order) ? 'bg-warning-50 border-l-4 border-l-warning-400' : ''
                }`}
              >
                {displayColumns.map((column) => (
                  <td key={column} className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <EditableCell 
                      order={order} 
                      column={column} 
                      value={order[column]} 
                      isEditable={editableColumns.includes(column)}
                    />
                  </td>
                ))}
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
