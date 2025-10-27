import { useState, useEffect } from 'react'
import { ChevronDownIcon, CalendarDaysIcon } from '@heroicons/react/24/outline'
import DatePicker from 'react-datepicker'
import 'react-datepicker/dist/react-datepicker.css'

export type DateFilterOption =
  | 'today'
  | 'this_week'
  | 'this_month'
  | 'last_month'
  | 'year_to_date'
  | 'all_time'
  | 'custom'

interface DateFilterProps {
  selectedFilter: DateFilterOption
  onFilterChange: (filter: DateFilterOption, startDate?: string, endDate?: string) => void
  className?: string
}

export default function DateFilter({ selectedFilter, onFilterChange, className = '' }: DateFilterProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [customStartDate, setCustomStartDate] = useState<Date | null>(null)
  const [customEndDate, setCustomEndDate] = useState<Date | null>(null)
  const [showCustomPicker, setShowCustomPicker] = useState(false)

  const filterOptions = [
    { value: 'today' as DateFilterOption, label: 'Today', icon: '📅' },
    { value: 'this_week' as DateFilterOption, label: 'This Week', icon: '📊' },
    { value: 'this_month' as DateFilterOption, label: 'This Month', icon: '📈' },
    { value: 'last_month' as DateFilterOption, label: 'Last Month', icon: '📉' },
    { value: 'year_to_date' as DateFilterOption, label: 'Year to Date', icon: '📅' },
    { value: 'all_time' as DateFilterOption, label: 'All Time', icon: '🔄' },
    { value: 'custom' as DateFilterOption, label: 'Custom Range', icon: '📆' },
  ]

  const getCurrentFilterLabel = () => {
    const option = filterOptions.find(opt => opt.value === selectedFilter)
    if (option) {
      return `${option.icon} ${option.label}`
    }
    return 'Select Date Range'
  }

  const handleFilterSelect = (filter: DateFilterOption) => {
    if (filter === 'custom') {
      setShowCustomPicker(true)
      setIsOpen(false)
    } else {
      onFilterChange(filter)
      setIsOpen(false)
      setShowCustomPicker(false)
    }
  }

  const handleCustomDateConfirm = () => {
    if (customStartDate && customEndDate) {
      const startStr = customStartDate.toISOString().split('T')[0]
      const endStr = customEndDate.toISOString().split('T')[0]
      onFilterChange('custom', startStr, endStr)
      setShowCustomPicker(false)
      setIsOpen(false)
    }
  }

  const handleCustomDateCancel = () => {
    setShowCustomPicker(false)
    setCustomStartDate(null)
    setCustomEndDate(null)
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element
      if (!target.closest('.date-filter-dropdown')) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className={`relative date-filter-dropdown ${className}`}>
      {/* Main Filter Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-200"
      >
        <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
          {getCurrentFilterLabel()}
        </span>
        <ChevronDownIcon
          className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${
            isOpen ? 'transform rotate-180' : ''
          }`}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute z-50 mt-2 w-full bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg">
          <div className="py-1 max-h-60 overflow-y-auto">
            {filterOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => handleFilterSelect(option.value)}
                className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-150 flex items-center space-x-3 ${
                  selectedFilter === option.value
                    ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400'
                    : 'text-gray-700 dark:text-gray-200'
                }`}
              >
                <span className="text-lg">{option.icon}</span>
                <span>{option.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Custom Date Picker Modal */}
      {showCustomPicker && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="px-6 py-4 border-b border-gray-300 dark:border-gray-600">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center">
                <CalendarDaysIcon className="w-5 h-5 mr-2" />
                Select Custom Date Range
              </h3>
            </div>

            <div className="px-6 py-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Start Date
                </label>
                <DatePicker
                  selected={customStartDate}
                  onChange={(date) => setCustomStartDate(date)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-200"
                  placeholderText="Select start date"
                  dateFormat="yyyy-MM-dd"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  End Date
                </label>
                <DatePicker
                  selected={customEndDate}
                  onChange={(date) => setCustomEndDate(date)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-gray-200"
                  placeholderText="Select end date"
                  dateFormat="yyyy-MM-dd"
                  minDate={customStartDate || undefined}
                />
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-300 dark:border-gray-600 flex justify-end space-x-3">
              <button
                onClick={handleCustomDateCancel}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors duration-200"
              >
                Cancel
              </button>
              <button
                onClick={handleCustomDateConfirm}
                disabled={!customStartDate || !customEndDate}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors duration-200"
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
