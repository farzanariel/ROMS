import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  ChevronDownIcon,
  ChevronRightIcon as ChevronRightIconMini,
  ArrowUpIcon,
  ArrowDownIcon,
  PencilIcon,
  CheckIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'
import { updateCell } from '../services/api'
import toast from 'react-hot-toast'

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
  _row_id?: string
}

interface EditableOrderTableProps {
  orders: Order[]
  sheetUrl: string
  showPendingHighlight?: boolean
  onDataChange?: () => void
  disablePagination?: boolean
}

interface EditingCell {
  rowId: string
  column: string
  value: string
}

interface ProductGroup {
  product: string
  orders: Order[]
  totalQuantity: number
  totalPrice: number
  avgPrice: number
}

export default function EditableOrderTable({ 
  orders, 
  sheetUrl, 
  showPendingHighlight = false,
  onDataChange,
  disablePagination = false
}: EditableOrderTableProps) {
  const [sortField, setSortField] = useState<keyof Order>('Date')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')
  const [editingCell, setEditingCell] = useState<EditingCell | null>(null)
  const [groupByProduct, setGroupByProduct] = useState(false)
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set())
  const [hiddenColumns, setHiddenColumns] = useState<Set<string>>(new Set())
  const [displayedItemCount, setDisplayedItemCount] = useState(50)
  const loadMoreRef = useRef<HTMLDivElement>(null)
  const itemsPerPage = 50

  const queryClient = useQueryClient()

  // Infinite scroll observer
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !groupByProduct) {
          // Load more items when scrolled to bottom
          setDisplayedItemCount(prev => Math.min(prev + itemsPerPage, orders.length))
        }
      },
      { threshold: 0.1 }
    )

    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current)
    }

    return () => {
      if (loadMoreRef.current) {
        observer.unobserve(loadMoreRef.current)
      }
    }
  }, [groupByProduct, orders.length, itemsPerPage])

  // Reset displayed count when switching views or when orders change
  useEffect(() => {
    setDisplayedItemCount(50)
  }, [groupByProduct, orders.length])

  // Mutation for updating cells
  const cellUpdateMutation = useMutation({
    mutationFn: ({ rowId, column, value }: { rowId: string, column: string, value: string }) => {
      console.log('🔄 Updating cell:', { rowId, column, value, sheetUrl })
      return updateCell(sheetUrl, { row_id: rowId, column, value })
    },
    onSuccess: (data, variables) => {
      console.log('✅ Cell updated successfully:', data)
      if (variables.column.toLowerCase().includes('tracking')) {
        toast.success('Tracking number updated! Order will be removed from pending list.')
      } else {
        toast.success(`Updated ${variables.column}`)
      }
      
      queryClient.invalidateQueries({ queryKey: ['orders-overview'] })
      queryClient.invalidateQueries({ queryKey: ['pending-orders'] })
      queryClient.invalidateQueries({ queryKey: ['all-orders'] })
      onDataChange?.()
    },
    onError: (error: any, variables) => {
      console.error('❌ Cell update failed:', error)
      toast.error(`Failed to update ${variables.column}: ${error.response?.data?.detail || error.message}`)
    }
  })

  // Column definitions with visibility toggle capability
  const allColumns = [
    { key: 'Date', label: 'Date', collapsible: false, width: 'w-24' },
    { key: 'Product', label: 'Product', collapsible: false, width: 'w-48' },
    { key: 'Price', label: 'Price', collapsible: true, width: 'w-24' },
    { key: 'Quantity', label: 'Qty', collapsible: true, width: 'w-16' },
    { key: 'QTY Received', label: 'Received', collapsible: true, width: 'w-20' },
    { key: 'Total', label: 'Total', collapsible: true, width: 'w-24' },
    { key: 'Status', label: 'Status', collapsible: false, width: 'w-24' },
    { key: 'Tracking Number', label: 'Tracking', collapsible: true, width: 'w-32' },
    { key: 'Order Number', label: 'Order #', collapsible: false, width: 'w-28' },
    { key: 'Profile', label: 'Profile', collapsible: true, width: 'w-32' }
  ]

  const visibleColumns = allColumns.filter(col => !hiddenColumns.has(col.key))
  const collapsibleColumns = allColumns.filter(col => col.collapsible)

  // Editable columns
  const editableColumns = [
    'Product', 'Price', 'Total', 'Commission', 'Quantity', 
    'Tracking Number', 'Status', 'QTY Received', 'Reference #'
  ]

  // Group orders by product
  const productGroups = useMemo(() => {
    if (!groupByProduct) return []

    const groups = new Map<string, ProductGroup>()
    
    orders.forEach(order => {
      const product = order.Product || 'Unknown Product'
      if (!groups.has(product)) {
        groups.set(product, {
          product,
          orders: [],
          totalQuantity: 0,
          totalPrice: 0,
          avgPrice: 0
        })
      }
      
      const group = groups.get(product)!
      group.orders.push(order)
      group.totalQuantity += Number(order.Quantity) || 0
      const price = parseFloat(String(order.Price || '0').replace(/[$,]/g, ''))
      group.totalPrice += price * (Number(order.Quantity) || 0)
    })

    // Calculate average price
    groups.forEach(group => {
      group.avgPrice = group.totalQuantity > 0 ? group.totalPrice / group.totalQuantity : 0
    })

    return Array.from(groups.values())
  }, [orders, groupByProduct])

  // Sort orders
  const sortedOrders = useMemo(() => {
    return [...orders].sort((a, b) => {
      let aValue = a[sortField] || ''
      let bValue = b[sortField] || ''
      
      if (sortField === 'Date' || sortField === 'Posted Date') {
        aValue = new Date(aValue || 0).getTime()
        bValue = new Date(bValue || 0).getTime()
      } else if (typeof aValue === 'string') {
        aValue = aValue.toLowerCase()
        bValue = typeof bValue === 'string' ? bValue.toLowerCase() : String(bValue).toLowerCase()
      }
      
      if (sortDirection === 'asc') {
        return (aValue || 0) > (bValue || 0) ? 1 : -1
      } else {
        return (aValue || 0) < (bValue || 0) ? 1 : -1
      }
    })
  }, [orders, sortField, sortDirection])

  // Display logic - show all for grouped view, use infinite scroll for list view
  const displayedOrders = groupByProduct 
    ? sortedOrders // Show all orders when grouped (they're hidden under groups anyway)
    : sortedOrders.slice(0, displayedItemCount) // Infinite scroll for list view
  
  const hasMore = displayedItemCount < sortedOrders.length

  const handleSort = (field: keyof Order) => {
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
      value: currentValue
    })
  }, [editableColumns])

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

  const toggleGroup = (product: string) => {
    const newExpanded = new Set(expandedGroups)
    if (newExpanded.has(product)) {
      newExpanded.delete(product)
    } else {
      newExpanded.add(product)
    }
    setExpandedGroups(newExpanded)
  }

  const toggleColumn = (columnKey: string) => {
    const newHidden = new Set(hiddenColumns)
    if (newHidden.has(columnKey)) {
      newHidden.delete(columnKey)
    } else {
      newHidden.add(columnKey)
    }
    setHiddenColumns(newHidden)
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
      <ArrowUpIcon className="h-3 w-3" />
    ) : (
      <ArrowDownIcon className="h-3 w-3" />
    )
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
    const displayValue = value || ''

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
            className="w-full px-1 py-0.5 text-xs border border-blue-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
            autoFocus
          />
          <button
            onClick={handleSaveEdit}
            className="p-0.5 text-green-600 hover:text-green-800 flex-shrink-0"
            disabled={cellUpdateMutation.isPending}
          >
            <CheckIcon className="h-3 w-3" />
          </button>
          <button
            onClick={handleCancelEdit}
            className="p-0.5 text-red-600 hover:text-red-800 flex-shrink-0"
          >
            <XMarkIcon className="h-3 w-3" />
          </button>
        </div>
      )
    }

    return (
      <div 
        className={`group flex items-center justify-between text-xs ${
          isEditable ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 px-1 py-0.5 rounded' : ''
        }`}
        onClick={() => isEditable && handleCellEdit(order._row_id!, column, String(displayValue))}
      >
        <span className="truncate">{displayValue}</span>
        {isEditable && (
          <PencilIcon className="h-2.5 w-2.5 text-gray-500 dark:text-gray-300 opacity-0 group-hover:opacity-100 ml-1 flex-shrink-0" />
        )}
      </div>
    )
  }

  return (
    <div className="card p-2">
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3 p-2 bg-gray-50 dark:bg-gray-800 rounded-md">
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setGroupByProduct(!groupByProduct)}
            className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
              groupByProduct 
                ? 'bg-primary-600 text-white' 
                : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600'
            }`}
          >
            {groupByProduct ? '📦 Grouped by Product' : '📋 List View'}
          </button>
          
          {/* Column visibility dropdown */}
          <div className="relative group">
            <button className="px-3 py-1 text-xs font-medium rounded-md bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600">
              👁️ Columns ({visibleColumns.length}/{allColumns.length})
            </button>
            <div className="absolute left-0 top-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg z-10 hidden group-hover:block min-w-[200px]">
              <div className="p-2">
                <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">Toggle Columns</div>
                {collapsibleColumns.map(col => (
                  <label key={col.key} className="flex items-center space-x-2 py-1 hover:bg-gray-50 dark:hover:bg-gray-700 px-2 rounded cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!hiddenColumns.has(col.key)}
                      onChange={() => toggleColumn(col.key)}
                      className="rounded"
                    />
                    <span className="text-xs">{col.label}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        </div>
        
        <div className="text-xs text-gray-600 dark:text-gray-400">
          {groupByProduct 
            ? `${productGroups.length} products • ${orders.length} orders` 
            : `Showing ${displayedItemCount} of ${orders.length} orders`}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 text-xs">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              {groupByProduct && (
                <th className="px-2 py-2 text-left w-8"></th>
              )}
              {visibleColumns.map(({ key, label }) => (
                <th
                  key={key}
                  onClick={() => !groupByProduct && handleSort(key as keyof Order)}
                  className={`px-2 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider ${
                    !groupByProduct ? 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600' : ''
                  }`}
                >
                  <div className="flex items-center space-x-1">
                    <span>{label}</span>
                    {!groupByProduct && <SortIcon field={key as keyof Order} />}
                    {editableColumns.includes(key) && (
                      <PencilIcon className="h-2.5 w-2.5 text-primary-500 dark:text-primary-400" />
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {groupByProduct ? (
              // Grouped view
              productGroups.map((group) => {
                const isExpanded = expandedGroups.has(group.product)
                return (
                  <>
                    <tr 
                      key={`group-${group.product}`}
                      className="bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/30 cursor-pointer font-medium"
                      onClick={() => toggleGroup(group.product)}
                    >
                      <td className="px-2 py-2">
                        {isExpanded ? (
                          <ChevronDownIcon className="h-4 w-4" />
                        ) : (
                          <ChevronRightIconMini className="h-4 w-4" />
                        )}
                      </td>
                      <td className="px-2 py-2 text-xs" colSpan={2}>
                        <div className="font-semibold">{group.product}</div>
                        <div className="text-gray-500 text-xs">
                          {group.orders.length} orders
                        </div>
                      </td>
                      {!hiddenColumns.has('Price') && (
                        <td className="px-2 py-2 text-xs">
                          ${group.avgPrice.toFixed(2)}
                        </td>
                      )}
                      {!hiddenColumns.has('Quantity') && (
                        <td className="px-2 py-2 text-xs text-center">
                          {group.totalQuantity}
                        </td>
                      )}
                      {!hiddenColumns.has('QTY Received') && (
                        <td className="px-2 py-2 text-xs text-center">
                          {group.orders.reduce((sum, o) => sum + (o['QTY Received'] || 0), 0)}
                        </td>
                      )}
                      {!hiddenColumns.has('Total') && (
                        <td className="px-2 py-2 text-xs font-semibold">
                          ${group.totalPrice.toFixed(2)}
                        </td>
                      )}
                      <td className="px-2 py-2 text-xs" colSpan={visibleColumns.length - 6}></td>
                    </tr>
                    
                    {isExpanded && group.orders.map((order, idx) => (
                      <tr 
                        key={order._row_id || idx}
                        className={`hover:bg-gray-50 dark:hover:bg-gray-700 ${
                          showPendingHighlight && isPendingOrder(order) ? 'bg-warning-50 dark:bg-warning-900/20 border-l-4 border-l-warning-400' : ''
                        }`}
                      >
                        <td className="px-2 py-2"></td>
                        {visibleColumns.map(({ key }) => (
                          <td key={key} className="px-2 py-2 text-xs">
                            {key === 'Date' ? (
                              order.Date ? new Date(order.Date).toLocaleDateString() : '-'
                            ) : key === 'Status' ? (
                              editableColumns.includes('Status') ? (
                                <EditableCell 
                                  order={order} 
                                  column="Status" 
                                  value={order.Status} 
                                  isEditable={true}
                                />
                              ) : (
                                getStatusBadge(order.Status || 'Unverified')
                              )
                            ) : key === 'QTY Received' ? (
                              <span className={
                                order['QTY Received'] < order.Quantity 
                                  ? 'text-warning-600 font-semibold' 
                                  : 'text-success-600'
                              }>
                                <EditableCell 
                                  order={order} 
                                  column={key} 
                                  value={order[key as keyof Order]} 
                                  isEditable={editableColumns.includes(key)}
                                />
                              </span>
                            ) : (
                              <EditableCell 
                                order={order} 
                                column={key} 
                                value={order[key as keyof Order]} 
                                isEditable={editableColumns.includes(key)}
                              />
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </>
                )
              })
            ) : (
              // List view
              displayedOrders.map((order, index) => (
                <tr 
                  key={order._row_id || index} 
                  className={`hover:bg-gray-50 dark:hover:bg-gray-700 ${
                    showPendingHighlight && isPendingOrder(order) ? 'bg-warning-50 dark:bg-warning-900/20 border-l-4 border-l-warning-400' : ''
                  }`}
                >
                  {visibleColumns.map(({ key }) => (
                    <td key={key} className="px-2 py-2 text-xs">
                      {key === 'Date' ? (
                        order.Date ? new Date(order.Date).toLocaleDateString() : '-'
                      ) : key === 'Status' ? (
                        editableColumns.includes('Status') ? (
                          <EditableCell 
                            order={order} 
                            column="Status" 
                            value={order.Status} 
                            isEditable={true}
                          />
                        ) : (
                          getStatusBadge(order.Status || 'Unverified')
                        )
                      ) : key === 'QTY Received' ? (
                        <span className={
                          order['QTY Received'] < order.Quantity 
                            ? 'text-warning-600 font-semibold' 
                            : 'text-success-600'
                        }>
                          <EditableCell 
                            order={order} 
                            column={key} 
                            value={order[key as keyof Order]} 
                            isEditable={editableColumns.includes(key)}
                          />
                        </span>
                      ) : key === 'Tracking Number' ? (
                        order['Tracking Number'] ? (
                          <EditableCell 
                            order={order} 
                            column="Tracking Number" 
                            value={order['Tracking Number']} 
                            isEditable={editableColumns.includes('Tracking Number')}
                          />
                        ) : (
                          <EditableCell 
                            order={order} 
                            column="Tracking Number" 
                            value="No tracking" 
                            isEditable={editableColumns.includes('Tracking Number')}
                          />
                        )
                      ) : (
                        <EditableCell 
                          order={order} 
                          column={key} 
                          value={order[key as keyof Order]} 
                          isEditable={editableColumns.includes(key)}
                        />
                      )}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Infinite scroll loading indicator */}
      {!groupByProduct && (
        <div className="px-2 py-3 border-t border-gray-200 dark:border-gray-700">
          <div className="text-center text-xs text-gray-500 dark:text-gray-400">
            Showing {displayedItemCount} of {sortedOrders.length} orders
          </div>
          {hasMore && (
            <div ref={loadMoreRef} className="flex items-center justify-center py-4">
              <div className="animate-pulse flex space-x-2">
                <div className="w-2 h-2 bg-primary-500 rounded-full"></div>
                <div className="w-2 h-2 bg-primary-500 rounded-full"></div>
                <div className="w-2 h-2 bg-primary-500 rounded-full"></div>
              </div>
              <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">Loading more...</span>
            </div>
          )}
        </div>
      )}
      
      {/* Grouped view summary */}
      {groupByProduct && (
        <div className="px-2 py-3 border-t border-gray-200 dark:border-gray-700">
          <div className="text-center text-xs text-gray-500 dark:text-gray-400">
            {productGroups.length} products • {orders.length} total orders
          </div>
        </div>
      )}
    </div>
  )
}
