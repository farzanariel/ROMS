import { useState, useEffect } from 'react'
import {
  Cog6ToothIcon,
  BugAntIcon,
  CodeBracketIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'

type Tab = 'general' | 'debugging' | 'api'

export default function Settings() {
  const [activeTab, setActiveTab] = useState<Tab>('general')
  const [queueStats, setQueueStats] = useState<any>(null)
  const [webhookLogs, setWebhookLogs] = useState<any>(null)

  const tabs = [
    { id: 'general' as Tab, name: 'General', icon: Cog6ToothIcon },
    { id: 'debugging' as Tab, name: 'Debugging', icon: BugAntIcon },
    { id: 'api' as Tab, name: 'API Info', icon: CodeBracketIcon },
  ]

  // Fetch debugging data
  useEffect(() => {
    if (activeTab === 'debugging') {
      fetchDebugData()
    }
  }, [activeTab])

  const fetchDebugData = async () => {
    try {
      const [queueRes, logsRes] = await Promise.all([
        fetch('http://localhost:8001/api/v2/webhooks/queue/stats'),
        fetch('http://localhost:8001/api/v2/webhooks/logs?limit=10'),
      ])
      
      if (queueRes.ok) setQueueStats(await queueRes.json())
      if (logsRes.ok) setWebhookLogs(await logsRes.json())
    } catch (error) {
      console.error('Failed to fetch debug data:', error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 w-full">
      <div className="max-w-7xl px-4 py-6 sm:px-6 lg:px-8 mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
          <p className="mt-1 text-sm text-gray-600">
            Manage your system configuration and view debugging information
          </p>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200 mb-6">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id
              
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    group inline-flex items-center py-4 px-1 border-b-2 font-medium text-sm
                    ${isActive
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }
                  `}
                >
                  <Icon className={`-ml-0.5 mr-2 h-5 w-5 ${isActive ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'}`} />
                  {tab.name}
                </button>
              )
            })}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="bg-white shadow-sm rounded-lg">
          {activeTab === 'general' && <GeneralSettings />}
          {activeTab === 'debugging' && <DebuggingInfo stats={queueStats} logs={webhookLogs} onRefresh={fetchDebugData} />}
          {activeTab === 'api' && <APIInfo />}
        </div>
      </div>
    </div>
  )
}

// General Settings Tab
function GeneralSettings() {
  return (
    <div className="p-6">
      <h2 className="text-lg font-medium text-gray-900 mb-4">General Settings</h2>
      
      <div className="space-y-6">
        {/* System Info */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-3">System Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-xs text-gray-500">Version</p>
              <p className="text-sm font-medium text-gray-900">2.0.0</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-xs text-gray-500">Environment</p>
              <p className="text-sm font-medium text-gray-900">Development</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-xs text-gray-500">Backend URL</p>
              <p className="text-sm font-medium text-gray-900">http://localhost:8001</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <p className="text-xs text-gray-500">WebSocket URL</p>
              <p className="text-sm font-medium text-gray-900">ws://localhost:8001/ws</p>
            </div>
          </div>
        </div>

        {/* Preferences */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-3">Preferences</h3>
          <div className="space-y-3">
            <label className="flex items-center">
              <input type="checkbox" className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" defaultChecked />
              <span className="ml-2 text-sm text-gray-700">Enable auto-refresh</span>
            </label>
            <label className="flex items-center">
              <input type="checkbox" className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" defaultChecked />
              <span className="ml-2 text-sm text-gray-700">Show WebSocket connection status</span>
            </label>
            <label className="flex items-center">
              <input type="checkbox" className="rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
              <span className="ml-2 text-sm text-gray-700">Enable desktop notifications</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  )
}

// Debugging Tab
function DebuggingInfo({ stats, logs, onRefresh }: { stats: any, logs: any, onRefresh: () => void }) {
  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium text-gray-900">Debugging Information</h2>
        <button
          onClick={onRefresh}
          className="px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-700"
        >
          Refresh Data
        </button>
      </div>

      <div className="space-y-6">
        {/* Queue Stats */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center">
            <span>Webhook Queue Statistics</span>
            {stats && (
              <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${
                stats.status === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
              }`}>
                {stats.status}
              </span>
            )}
          </h3>
          
          {stats ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-xs text-gray-500">Queue Size</p>
                <p className="text-2xl font-bold text-gray-900">{stats.queue_size}</p>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-xs text-gray-500">Peak Size</p>
                <p className="text-2xl font-bold text-gray-900">{stats.queue_size_peak}</p>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-xs text-gray-500">Total Received</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total_received}</p>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-xs text-gray-500">Total Processed</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total_processed}</p>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-xs text-gray-500">Success Rate</p>
                <p className="text-2xl font-bold text-green-600">{stats.success_rate}%</p>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-xs text-gray-500">Workers Running</p>
                <p className="text-2xl font-bold text-gray-900">{stats.workers_running}/{stats.workers_total}</p>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-xs text-gray-500">Avg Processing</p>
                <p className="text-2xl font-bold text-gray-900">{stats.avg_processing_time_ms}ms</p>
              </div>
              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-xs text-gray-500">Failed</p>
                <p className="text-2xl font-bold text-red-600">{stats.total_failed}</p>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">Loading stats...</div>
          )}
        </div>

        {/* Recent Webhook Logs */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-3">Recent Webhook Logs (Last 10)</h3>
          
          {logs ? (
            <div className="overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Endpoint</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Processed</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {logs.logs.map((log: any) => (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-900">{log.id}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{log.endpoint}</td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`inline-flex px-2 py-1 text-xs rounded-full ${
                          log.status_code === 200 || log.status_code === 202 ? 'bg-green-100 text-green-800' :
                          log.status_code === 400 ? 'bg-yellow-100 text-yellow-800' :
                          'bg-red-100 text-red-800'
                        }`}>
                          {log.status_code}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {log.processed ? (
                          <CheckCircleIcon className="h-5 w-5 text-green-500" />
                        ) : (
                          <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">Loading logs...</div>
          )}
        </div>
      </div>
    </div>
  )
}

// API Info Tab
function APIInfo() {
  const apiEndpoints = [
    {
      category: 'Orders',
      endpoints: [
        { method: 'GET', path: '/api/v2/orders', description: 'Get all orders with pagination' },
        { method: 'GET', path: '/api/v2/orders/{id}', description: 'Get single order by ID' },
      ]
    },
    {
      category: 'Webhooks',
      endpoints: [
        { method: 'POST', path: '/api/v2/webhooks/orders', description: 'Receive order webhook (main endpoint)' },
        { method: 'GET', path: '/api/v2/webhooks/logs', description: 'Get webhook logs' },
        { method: 'GET', path: '/api/v2/webhooks/queue/stats', description: 'Get queue statistics' },
        { method: 'GET', path: '/api/v2/webhooks/queue/dead-letters', description: 'Get failed messages' },
        { method: 'POST', path: '/api/v2/webhooks/queue/retry-failed', description: 'Retry failed webhooks' },
      ]
    },
    {
      category: 'System',
      endpoints: [
        { method: 'GET', path: '/health', description: 'Health check endpoint' },
        { method: 'GET', path: '/ws', description: 'WebSocket connection for real-time updates' },
      ]
    }
  ]

  return (
    <div className="p-6">
      <h2 className="text-lg font-medium text-gray-900 mb-4">API Information</h2>

      <div className="space-y-6">
        {/* API Base URLs */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-3">Base URLs</h3>
          <div className="space-y-2">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-xs text-blue-600 font-medium mb-1">REST API</p>
              <code className="text-sm text-blue-900">http://localhost:8001</code>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-xs text-green-600 font-medium mb-1">WebSocket</p>
              <code className="text-sm text-green-900">ws://localhost:8001/ws</code>
            </div>
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <p className="text-xs text-purple-600 font-medium mb-1">Webhook URL (for Refract)</p>
              <code className="text-sm text-purple-900">http://localhost:8001/api/v2/webhooks/orders</code>
            </div>
          </div>
        </div>

        {/* API Endpoints */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-3">Available Endpoints</h3>
          
          {apiEndpoints.map((category) => (
            <div key={category.category} className="mb-6">
              <h4 className="text-sm font-medium text-gray-600 mb-2">{category.category}</h4>
              <div className="space-y-2">
                {category.endpoints.map((endpoint, idx) => (
                  <div key={idx} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                    <div className="flex items-start">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded ${
                        endpoint.method === 'GET' ? 'bg-blue-100 text-blue-800' :
                        endpoint.method === 'POST' ? 'bg-green-100 text-green-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {endpoint.method}
                      </span>
                      <div className="ml-3 flex-1">
                        <code className="text-sm font-mono text-gray-900">{endpoint.path}</code>
                        <p className="text-xs text-gray-600 mt-1">{endpoint.description}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Quick Links */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-3">Quick Links</h3>
          <div className="space-y-2">
            <a
              href="http://localhost:8001/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="block bg-gray-50 border border-gray-200 rounded-lg p-3 hover:bg-gray-100 transition-colors"
            >
              <p className="text-sm font-medium text-gray-900">Interactive API Documentation</p>
              <p className="text-xs text-gray-600">Full API docs with try-it-out functionality</p>
            </a>
            <a
              href="http://localhost:8001/health"
              target="_blank"
              rel="noopener noreferrer"
              className="block bg-gray-50 border border-gray-200 rounded-lg p-3 hover:bg-gray-100 transition-colors"
            >
              <p className="text-sm font-medium text-gray-900">Health Check</p>
              <p className="text-xs text-gray-600">Verify backend is running</p>
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}

