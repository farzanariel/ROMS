import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { 
  ChevronDownIcon,
  DocumentTextIcon,
  CheckIcon
} from '@heroicons/react/24/outline'
import { fetchWorksheets } from '../services/api'

interface WorksheetSelectorProps {
  sheetUrl: string
  selectedWorksheet?: string
  onWorksheetChange: (worksheet: string | undefined) => void
  showAllOption?: boolean
}

export default function WorksheetSelector({ 
  sheetUrl, 
  selectedWorksheet, 
  onWorksheetChange,
  showAllOption = true 
}: WorksheetSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)

  const { data: worksheetData, isLoading } = useQuery({
    queryKey: ['worksheets', sheetUrl],
    queryFn: () => fetchWorksheets(sheetUrl),
    enabled: !!sheetUrl,
  })

  const worksheets = worksheetData?.worksheets || []

  const handleSelect = (worksheet: string | undefined) => {
    onWorksheetChange(worksheet)
    setIsOpen(false)
  }

  const selectedLabel = selectedWorksheet 
    ? `📄 ${selectedWorksheet}` 
    : showAllOption 
      ? '📊 All Product Runs' 
      : 'Select Worksheet'

  if (!sheetUrl || isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-10 bg-gray-200 rounded-md w-48"></div>
      </div>
    )
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full px-4 py-2 text-left bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
      >
        <div className="flex items-center space-x-2">
          <DocumentTextIcon className="h-4 w-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-700 truncate max-w-48">
            {selectedLabel}
          </span>
        </div>
        <ChevronDownIcon 
          className={`h-4 w-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} 
        />
      </button>

      {isOpen && (
        <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto">
          {showAllOption && (
            <button
              onClick={() => handleSelect(undefined)}
              className="flex items-center justify-between w-full px-4 py-3 text-left hover:bg-gray-50 focus:outline-none focus:bg-gray-50"
            >
              <div className="flex items-center space-x-2">
                <DocumentTextIcon className="h-4 w-4 text-primary-500" />
                <span className="text-sm text-gray-900">📊 All Product Runs</span>
              </div>
              {!selectedWorksheet && (
                <CheckIcon className="h-4 w-4 text-primary-500" />
              )}
            </button>
          )}
          
          {worksheets.map((worksheet: string) => (
            <button
              key={worksheet}
              onClick={() => handleSelect(worksheet)}
              className="flex items-center justify-between w-full px-4 py-3 text-left hover:bg-gray-50 focus:outline-none focus:bg-gray-50"
            >
              <div className="flex items-center space-x-2">
                <DocumentTextIcon className="h-4 w-4 text-gray-400" />
                <span className="text-sm text-gray-900">📄 {worksheet}</span>
              </div>
              {selectedWorksheet === worksheet && (
                <CheckIcon className="h-4 w-4 text-primary-500" />
              )}
            </button>
          ))}
          
          {worksheets.length === 0 && (
            <div className="px-4 py-3 text-sm text-gray-500">
              No worksheets found
            </div>
          )}
        </div>
      )}
      
      {worksheets.length > 0 && (
        <div className="mt-2 text-xs text-gray-500">
          {worksheets.length} product run{worksheets.length !== 1 ? 's' : ''} available
        </div>
      )}
    </div>
  )
}
