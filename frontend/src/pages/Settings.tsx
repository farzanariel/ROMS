import { useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { 
  CogIcon, 
  LinkIcon, 
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  SunIcon,
  MoonIcon,
  DocumentArrowDownIcon,
  DocumentArrowUpIcon,
  TrashIcon,
  UserCircleIcon,
  BellIcon,
  ShieldCheckIcon,
  ClockIcon,
  FolderIcon,
  EyeIcon,
  EyeSlashIcon,
  PencilIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline'
import { checkHealth, fetchWorksheets, fetchWorksheetConfig, updateWorksheetConfig, WorksheetInfo, WorksheetConfig } from '../services/api'
import { useDarkMode } from '../contexts/DarkModeContext'
import toast from 'react-hot-toast'

interface SettingsProps {
  sheetUrl: string
  onSheetUrlChange: (url: string) => void
}

// Worksheet Management Component
function WorksheetManagement({ sheetUrl }: { sheetUrl: string }) {
  const [configurations, setConfigurations] = useState<Record<string, WorksheetConfig>>({})
  const [editingWorksheet, setEditingWorksheet] = useState<string | null>(null)
  const [editForm, setEditForm] = useState<Partial<WorksheetConfig>>({})

  // Fetch worksheets
  const { data: worksheetsData, isLoading: isLoadingWorksheets, refetch: refetchWorksheets } = useQuery({
    queryKey: ['worksheets', sheetUrl],
    queryFn: () => fetchWorksheets(sheetUrl),
    enabled: !!sheetUrl,
    refetchInterval: 60000, // Refresh every minute
  })

  // Fetch configurations
  const { data: configData, isLoading: isLoadingConfig } = useQuery({
    queryKey: ['worksheet-config'],
    queryFn: fetchWorksheetConfig,
  })

  // Update configurations when data changes
  useEffect(() => {
    if (configData) {
      setConfigurations(configData.configurations)
    }
  }, [configData])

  // Default configuration for new worksheets
  const getDefaultConfig = (): WorksheetConfig => ({
    enabled: true,
    custom_name: '',
    priority: 0,
    refresh_interval: 300, // 5 minutes
    include_in_dashboard: true,
    include_in_reports: true,
    color_theme: 'blue',
    notes: ''
  })

  // Get configuration for a worksheet
  const getWorksheetConfig = (worksheetTitle: string): WorksheetConfig => {
    return configurations[worksheetTitle] || getDefaultConfig()
  }

  // Update configuration
  const handleConfigUpdate = async (worksheetTitle: string, updates: Partial<WorksheetConfig>) => {
    const currentConfig = getWorksheetConfig(worksheetTitle)
    const newConfig = { ...currentConfig, ...updates }
    
    const newConfigurations = {
      ...configurations,
      [worksheetTitle]: newConfig
    }
    
    setConfigurations(newConfigurations)
    
    try {
      await updateWorksheetConfig(newConfigurations)
      toast.success(`Updated configuration for ${worksheetTitle}`)
    } catch (error) {
      toast.error('Failed to save configuration')
      console.error('Config update error:', error)
    }
  }

  // Save edit form
  const handleSaveEdit = async () => {
    if (!editingWorksheet) return
    
    await handleConfigUpdate(editingWorksheet, editForm)
    setEditingWorksheet(null)
    setEditForm({})
  }

  // Cancel edit
  const handleCancelEdit = () => {
    setEditingWorksheet(null)
    setEditForm({})
  }

  // Start editing
  const handleStartEdit = (worksheetTitle: string) => {
    setEditingWorksheet(worksheetTitle)
    setEditForm(getWorksheetConfig(worksheetTitle))
  }

  // Get status badge color
  const getStatusColor = (worksheet: WorksheetInfo) => {
    if (worksheet.error) return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
    if (!getWorksheetConfig(worksheet.title).enabled) return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
    if (worksheet.data_rows > 0) return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
  }

  // Get status text
  const getStatusText = (worksheet: WorksheetInfo) => {
    if (worksheet.error) return 'Error'
    if (!getWorksheetConfig(worksheet.title).enabled) return 'Disabled'
    if (worksheet.data_rows > 0) return 'Active'
    return 'Empty'
  }

  if (!sheetUrl) {
    return (
      <div className="space-y-8">
        <div className="card">
          <div className="text-center py-12">
            <FolderIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">No Google Sheet Connected</h3>
            <p className="text-gray-500 dark:text-gray-400">
              Please configure your Google Sheets URL in the General tab to manage worksheets.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Header with refresh */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center">
              <FolderIcon className="h-5 w-5 mr-2" />
              Worksheet Management
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              Configure individual worksheets from your Google Sheet
            </p>
          </div>
          <button
            onClick={() => refetchWorksheets()}
            disabled={isLoadingWorksheets}
            className="btn-secondary flex items-center space-x-2"
          >
            <ArrowPathIcon className={`h-4 w-4 ${isLoadingWorksheets ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Summary Stats */}
        {worksheetsData && (
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {worksheetsData.total_count}
              </div>
              <div className="text-sm text-blue-800 dark:text-blue-300">Total Worksheets</div>
            </div>
            <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {worksheetsData.worksheets.filter(ws => getWorksheetConfig(ws.title).enabled).length}
              </div>
              <div className="text-sm text-green-800 dark:text-green-300">Enabled</div>
            </div>
            <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg">
              <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                {worksheetsData.worksheets.filter(ws => ws.data_rows > 0).length}
              </div>
              <div className="text-sm text-yellow-800 dark:text-yellow-300">With Data</div>
            </div>
            <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg">
              <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                {worksheetsData.worksheets.filter(ws => getWorksheetConfig(ws.title).include_in_dashboard).length}
              </div>
              <div className="text-sm text-purple-800 dark:text-purple-300">In Dashboard</div>
            </div>
          </div>
        )}
      </div>

      {/* Worksheets List */}
      <div className="card">
        <h3 className="text-md font-semibold text-gray-900 dark:text-gray-100 mb-4">Worksheets</h3>
        
        {isLoadingWorksheets || isLoadingConfig ? (
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="animate-pulse">
                <div className="h-20 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
              </div>
            ))}
          </div>
        ) : worksheetsData?.worksheets.length ? (
          <div className="space-y-4">
            {worksheetsData.worksheets.map((worksheet) => {
              const config = getWorksheetConfig(worksheet.title)
              const isEditing = editingWorksheet === worksheet.title

              return (
                <div
                  key={worksheet.id}
                  className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                >
                  {isEditing ? (
                    // Edit Mode
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium text-gray-900 dark:text-gray-100">{worksheet.title}</h4>
                        <div className="flex space-x-2">
                          <button
                            onClick={handleSaveEdit}
                            className="btn-primary text-sm px-3 py-1"
                          >
                            Save
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="btn-secondary text-sm px-3 py-1"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Custom Name
                          </label>
                          <input
                            type="text"
                            value={editForm.custom_name || ''}
                            onChange={(e) => setEditForm({ ...editForm, custom_name: e.target.value })}
                            placeholder={worksheet.title}
                            className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Priority
                          </label>
                          <input
                            type="number"
                            value={editForm.priority || 0}
                            onChange={(e) => setEditForm({ ...editForm, priority: parseInt(e.target.value) || 0 })}
                            min="0"
                            max="10"
                            className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Refresh Interval (seconds)
                          </label>
                          <select
                            value={editForm.refresh_interval || 300}
                            onChange={(e) => setEditForm({ ...editForm, refresh_interval: parseInt(e.target.value) })}
                            className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                          >
                            <option value={60}>1 minute</option>
                            <option value={300}>5 minutes</option>
                            <option value={600}>10 minutes</option>
                            <option value={1800}>30 minutes</option>
                            <option value={3600}>1 hour</option>
                          </select>
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Color Theme
                          </label>
                          <select
                            value={editForm.color_theme || 'blue'}
                            onChange={(e) => setEditForm({ ...editForm, color_theme: e.target.value })}
                            className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                          >
                            <option value="blue">Blue</option>
                            <option value="green">Green</option>
                            <option value="purple">Purple</option>
                            <option value="orange">Orange</option>
                            <option value="red">Red</option>
                          </select>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={editForm.include_in_dashboard || false}
                            onChange={(e) => setEditForm({ ...editForm, include_in_dashboard: e.target.checked })}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Include in Dashboard</span>
                        </label>

                        <label className="flex items-center">
                          <input
                            type="checkbox"
                            checked={editForm.include_in_reports || false}
                            onChange={(e) => setEditForm({ ...editForm, include_in_reports: e.target.checked })}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">Include in Reports</span>
                        </label>
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                          Notes
                        </label>
                        <textarea
                          value={editForm.notes || ''}
                          onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                          placeholder="Add notes about this worksheet..."
                          rows={2}
                          className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                        />
                      </div>
                    </div>
                  ) : (
                    // View Mode
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3">
                          <h4 className="font-medium text-gray-900 dark:text-gray-100">
                            {config.custom_name || worksheet.title}
                          </h4>
                          {config.custom_name && (
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                              ({worksheet.title})
                            </span>
                          )}
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(worksheet)}`}>
                            {getStatusText(worksheet)}
                          </span>
                          {config.priority > 0 && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300">
                              Priority {config.priority}
                            </span>
                          )}
                        </div>

                        <div className="flex items-center space-x-4 mt-2 text-sm text-gray-600 dark:text-gray-400">
                          <span>{worksheet.data_rows} rows with data</span>
                          <span>{worksheet.row_count} total rows</span>
                          <span>Refresh: {config.refresh_interval}s</span>
                          {worksheet.updated && (
                            <span>Updated: {new Date(worksheet.updated).toLocaleDateString()}</span>
                          )}
                        </div>

                        {config.notes && (
                          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 italic">
                            {config.notes}
                          </p>
                        )}

                        <div className="flex items-center space-x-4 mt-2">
                          {config.include_in_dashboard && (
                            <span className="inline-flex items-center text-xs text-blue-600 dark:text-blue-400">
                              <span className="w-2 h-2 bg-blue-600 dark:bg-blue-400 rounded-full mr-1"></span>
                              Dashboard
                            </span>
                          )}
                          {config.include_in_reports && (
                            <span className="inline-flex items-center text-xs text-green-600 dark:text-green-400">
                              <span className="w-2 h-2 bg-green-600 dark:bg-green-400 rounded-full mr-1"></span>
                              Reports
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => handleConfigUpdate(worksheet.title, { enabled: !config.enabled })}
                          className={`p-2 rounded-md transition-colors ${
                            config.enabled
                              ? 'text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20'
                              : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                          }`}
                          title={config.enabled ? 'Disable worksheet' : 'Enable worksheet'}
                        >
                          {config.enabled ? <EyeIcon className="h-4 w-4" /> : <EyeSlashIcon className="h-4 w-4" />}
                        </button>

                        <button
                          onClick={() => handleStartEdit(worksheet.title)}
                          className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                          title="Edit configuration"
                        >
                          <PencilIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="text-center py-12">
            <FolderIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">No Worksheets Found</h3>
            <p className="text-gray-500 dark:text-gray-400">
              No worksheets were found in the connected Google Sheet.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Settings({ sheetUrl, onSheetUrlChange }: SettingsProps) {
  const [tempSheetUrl, setTempSheetUrl] = useState(sheetUrl)
  const { isDarkMode, toggleDarkMode } = useDarkMode()
  const queryClient = useQueryClient()
  
  // New state for advanced settings
  const [debugMode, setDebugMode] = useState(() => localStorage.getItem('debug-mode') === 'true')
  const [cacheDuration, setCacheDuration] = useState(() => localStorage.getItem('cache-duration') || '5')
  const [emailNotifications, setEmailNotifications] = useState(() => localStorage.getItem('email-notifications') === 'true')
  const [pushNotifications, setPushNotifications] = useState(() => localStorage.getItem('push-notifications') === 'true')
  const [apiRateLimit, setApiRateLimit] = useState(() => localStorage.getItem('api-rate-limit') || '100')
  const [customApiEndpoint, setCustomApiEndpoint] = useState(() => localStorage.getItem('custom-api-endpoint') || '')
  const [activeTab, setActiveTab] = useState('general')

  const { data: health, refetch: refetchHealth } = useQuery({
    queryKey: ['health'],
    queryFn: checkHealth,
    refetchInterval: 30000,
  })

  const handleSaveSheetUrl = () => {
    if (!tempSheetUrl.trim()) {
      toast.error('Please enter a valid Google Sheets URL')
      return
    }

    if (!tempSheetUrl.includes('docs.google.com/spreadsheets')) {
      toast.error('Please enter a valid Google Sheets URL')
      return
    }

    onSheetUrlChange(tempSheetUrl.trim())
    toast.success('Google Sheets URL saved successfully!')
    refetchHealth()
  }

  const handleTestConnection = async () => {
    if (!sheetUrl) {
      toast.error('Please save a Google Sheets URL first')
      return
    }

    try {
      await refetchHealth()
      toast.success('Connection test successful!')
    } catch (error) {
      toast.error('Connection test failed. Please check your settings.')
    }
  }

  const handleReloadConnection = async () => {
    if (!sheetUrl) {
      toast.error('Please save a Google Sheets URL first')
      return
    }

    try {
      const loadingToast = toast.loading('Reloading Google connection...')
      await refetchHealth()
      queryClient.invalidateQueries()
      queryClient.removeQueries({ queryKey: ['orders-overview'] })
      queryClient.removeQueries({ queryKey: ['pending-orders'] })
      queryClient.removeQueries({ queryKey: ['all-orders'] })
      toast.dismiss(loadingToast)
      toast.success('Google connection reloaded successfully! Data will refresh on next page load.')
    } catch (error) {
      toast.error('Failed to reload connection. Please try again.')
    }
  }

  // Save settings to localStorage
  const saveAdvancedSettings = () => {
    localStorage.setItem('debug-mode', debugMode.toString())
    localStorage.setItem('cache-duration', cacheDuration)
    localStorage.setItem('email-notifications', emailNotifications.toString())
    localStorage.setItem('push-notifications', pushNotifications.toString())
    localStorage.setItem('api-rate-limit', apiRateLimit)
    localStorage.setItem('custom-api-endpoint', customApiEndpoint)
    toast.success('Advanced settings saved!')
  }

  // Export settings
  const exportSettings = () => {
    const settings = {
      sheetUrl,
      debugMode,
      cacheDuration,
      emailNotifications,
      pushNotifications,
      apiRateLimit,
      customApiEndpoint,
      darkMode: isDarkMode,
      hiddenSections: localStorage.getItem('dashboard-hidden-sections'),
      exportDate: new Date().toISOString()
    }
    
    const blob = new Blob([JSON.stringify(settings, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `dashboard-settings-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    toast.success('Settings exported successfully!')
  }

  // Import settings
  const importSettings = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const settings = JSON.parse(e.target?.result as string)
        
        if (settings.sheetUrl) onSheetUrlChange(settings.sheetUrl)
        if (settings.debugMode !== undefined) setDebugMode(settings.debugMode)
        if (settings.cacheDuration) setCacheDuration(settings.cacheDuration)
        if (settings.emailNotifications !== undefined) setEmailNotifications(settings.emailNotifications)
        if (settings.pushNotifications !== undefined) setPushNotifications(settings.pushNotifications)
        if (settings.apiRateLimit) setApiRateLimit(settings.apiRateLimit)
        if (settings.customApiEndpoint) setCustomApiEndpoint(settings.customApiEndpoint)
        if (settings.hiddenSections) localStorage.setItem('dashboard-hidden-sections', settings.hiddenSections)
        
        saveAdvancedSettings()
        toast.success('Settings imported successfully!')
      } catch (error) {
        toast.error('Invalid settings file')
      }
    }
    reader.readAsText(file)
  }

  // Clear cache
  const clearCache = () => {
    queryClient.clear()
    localStorage.removeItem('dashboard-hidden-sections')
    
    // Clear all localStorage items related to the dashboard
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith('dashboard-') || key.startsWith('cache-') || key.startsWith('debug-')) {
        localStorage.removeItem(key)
      }
    })
    
    toast.success('All cache and local data cleared successfully!')
  }

  const tabs = [
    { id: 'general', label: 'General', icon: CogIcon },
    { id: 'worksheets', label: 'Worksheets', icon: FolderIcon },
    { id: 'data', label: 'Data Management', icon: DocumentArrowDownIcon },
    { id: 'notifications', label: 'Notifications', icon: BellIcon },
    { id: 'advanced', label: 'Advanced', icon: ShieldCheckIcon },
    { id: 'profile', label: 'Profile', icon: UserCircleIcon }
  ]

  return (
    <div className="p-4 sm:p-6 lg:p-8 pb-20 lg:pb-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6 lg:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
          <p className="mt-2 text-sm sm:text-base text-gray-600 dark:text-gray-300">
            Configure your Google Sheets integration and dashboard preferences
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="border-b border-gray-200 dark:border-gray-700 mb-8">
          <nav className="-mb-px flex space-x-8 overflow-x-auto">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2 ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                </button>
              )
            })}
          </nav>
        </div>

        {/* General Tab */}
        {activeTab === 'general' && (
          <div className="space-y-8">
            {/* System Status */}
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <InformationCircleIcon className="h-5 w-5 mr-2" />
                System Status
              </h2>
              
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600 dark:text-gray-400">API Server</span>
                  <div className="flex items-center">
                    {health ? (
                      <>
                        <CheckCircleIcon className="h-5 w-5 text-success-500 mr-2" />
                        <span className="text-success-600 font-medium">Connected</span>
                      </>
                    ) : (
                      <>
                        <ExclamationTriangleIcon className="h-5 w-5 text-danger-500 mr-2" />
                        <span className="text-danger-600 font-medium">Disconnected</span>
                      </>
                    )}
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Google Sheets</span>
                  <div className="flex items-center">
                    {health?.google_sheets === 'connected' ? (
                      <>
                        <CheckCircleIcon className="h-5 w-5 text-success-500 mr-2" />
                        <span className="text-success-600 font-medium">Connected</span>
                      </>
                    ) : (
                      <>
                        <ExclamationTriangleIcon className="h-5 w-5 text-warning-500 mr-2" />
                        <span className="text-warning-600 font-medium">Not configured</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Google Sheets Configuration */}
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <LinkIcon className="h-5 w-5 mr-2" />
                Google Sheets Integration
              </h2>
              
              <div className="space-y-4">
                <div>
                  <label htmlFor="sheet-url" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Google Sheets URL
                  </label>
                  <input
                    type="url"
                    id="sheet-url"
                    value={tempSheetUrl}
                    onChange={(e) => setTempSheetUrl(e.target.value)}
                    placeholder="https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
                    className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  />
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Enter the full URL of your Google Sheets document with order data
                  </p>
                </div>
                
                <div className="flex space-x-3">
                  <button
                    onClick={handleSaveSheetUrl}
                    className="btn-primary"
                  >
                    Save URL
                  </button>
                  
                  <button
                    onClick={handleTestConnection}
                    className="btn-secondary"
                    disabled={!sheetUrl}
                  >
                    Test Connection
                  </button>
                </div>
              </div>
            </div>

            {/* Appearance Settings */}
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <CogIcon className="h-5 w-5 mr-2" />
                Appearance
              </h2>
              
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    {isDarkMode ? (
                      <MoonIcon className="h-5 w-5 text-gray-600 dark:text-gray-400 mr-3" />
                    ) : (
                      <SunIcon className="h-5 w-5 text-gray-600 dark:text-gray-400 mr-3" />
                    )}
                    <div>
                      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Dark Mode
                      </span>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
                      </p>
                    </div>
                  </div>
                  
                  <button
                    onClick={toggleDarkMode}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 ${
                      isDarkMode ? 'bg-primary-600' : 'bg-gray-200'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        isDarkMode ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Worksheets Tab */}
        {activeTab === 'worksheets' && <WorksheetManagement sheetUrl={sheetUrl} />}

        {/* Data Management Tab */}
        {activeTab === 'data' && (
          <div className="space-y-8">
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <DocumentArrowDownIcon className="h-5 w-5 mr-2" />
                Backup & Export
              </h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Export Settings</span>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Download all your settings as a JSON file</p>
                  </div>
                  <button
                    onClick={exportSettings}
                    className="btn-primary flex items-center space-x-2"
                  >
                    <DocumentArrowDownIcon className="h-4 w-4" />
                    <span>Export</span>
                  </button>
                </div>
                
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Import Settings</span>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Restore settings from a backup file</p>
                  </div>
                  <label className="btn-secondary flex items-center space-x-2 cursor-pointer">
                    <DocumentArrowUpIcon className="h-4 w-4" />
                    <span>Import</span>
                    <input
                      type="file"
                      accept=".json"
                      onChange={importSettings}
                      className="hidden"
                    />
                  </label>
                </div>
              </div>
            </div>

            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <TrashIcon className="h-5 w-5 mr-2" />
                Cache Management
              </h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Clear All Cache</span>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Remove all cached data and force fresh data load</p>
                  </div>
                  <button
                    onClick={clearCache}
                    className="btn-secondary flex items-center space-x-2"
                  >
                    <TrashIcon className="h-4 w-4" />
                    <span>Clear Cache</span>
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Reload Google Connection</span>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Force refresh of sheet data and connection</p>
                  </div>
                  <button
                    onClick={handleReloadConnection}
                    className="btn-primary"
                    disabled={!sheetUrl}
                  >
                    Reload Data
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Notifications Tab */}
        {activeTab === 'notifications' && (
          <div className="space-y-8">
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <BellIcon className="h-5 w-5 mr-2" />
                Notification Preferences
              </h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Email Notifications</span>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Receive important updates via email</p>
                  </div>
                  <button
                    onClick={() => {
                      setEmailNotifications(!emailNotifications)
                      localStorage.setItem('email-notifications', (!emailNotifications).toString())
                      toast.success(emailNotifications ? 'Email notifications disabled' : 'Email notifications enabled')
                    }}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      emailNotifications ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        emailNotifications ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Push Notifications</span>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Get real-time notifications in your browser</p>
                  </div>
                  <button
                    onClick={() => {
                      setPushNotifications(!pushNotifications)
                      localStorage.setItem('push-notifications', (!pushNotifications).toString())
                      toast.success(pushNotifications ? 'Push notifications disabled' : 'Push notifications enabled')
                    }}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      pushNotifications ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        pushNotifications ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Advanced Tab */}
        {activeTab === 'advanced' && (
          <div className="space-y-8">
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <ShieldCheckIcon className="h-5 w-5 mr-2" />
                Debug & Development
              </h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Debug Mode</span>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Show detailed console logs and debug information</p>
                  </div>
                  <button
                    onClick={() => {
                      setDebugMode(!debugMode)
                      localStorage.setItem('debug-mode', (!debugMode).toString())
                      toast.success(debugMode ? 'Debug mode disabled' : 'Debug mode enabled')
                    }}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      debugMode ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-600'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        debugMode ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
              </div>
            </div>

            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <ClockIcon className="h-5 w-5 mr-2" />
                Performance Settings
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Cache Duration (minutes)
                  </label>
                  <input
                    type="number"
                    value={cacheDuration}
                    onChange={(e) => {
                      setCacheDuration(e.target.value)
                      localStorage.setItem('cache-duration', e.target.value)
                      toast.success(`Cache duration updated to ${e.target.value} minutes`)
                    }}
                    min="1"
                    max="60"
                    className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">How long to cache data before refetching</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    API Rate Limit (requests/minute)
                  </label>
                  <input
                    type="number"
                    value={apiRateLimit}
                    onChange={(e) => {
                      setApiRateLimit(e.target.value)
                      localStorage.setItem('api-rate-limit', e.target.value)
                      toast.success(`API rate limit updated to ${e.target.value} requests/minute`)
                    }}
                    min="10"
                    max="1000"
                    className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Maximum API requests per minute</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Custom API Endpoint
                  </label>
                  <input
                    type="url"
                    value={customApiEndpoint}
                    onChange={(e) => {
                      setCustomApiEndpoint(e.target.value)
                      localStorage.setItem('custom-api-endpoint', e.target.value)
                      if (e.target.value) {
                        toast.success(`Custom API endpoint set to ${e.target.value}`)
                      } else {
                        toast.success('Using default API endpoint')
                      }
                    }}
                    placeholder="https://api.example.com"
                    className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Override default API endpoint (leave empty for default)</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div className="space-y-8">
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <UserCircleIcon className="h-5 w-5 mr-2" />
                User Information
              </h2>
              <div className="space-y-4">
                <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700">
                  <p className="text-sm text-blue-800 dark:text-blue-200">
                    <strong>Coming Soon:</strong> User profiles, session management, and access token controls.
                  </p>
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  <ul className="list-disc list-inside space-y-1">
                    <li>View and edit user profile information</li>
                    <li>Manage active sessions across devices</li>
                    <li>Generate and revoke API access tokens</li>
                    <li>View activity log and login history</li>
                    <li>Configure security preferences</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}