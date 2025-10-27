import { useState, useEffect } from 'react'
import {
  HomeIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  Bars3Icon,
  XMarkIcon,
} from '@heroicons/react/24/outline'

interface SidebarProps {
  currentPage: string
  onNavigate: (page: string) => void
  onCollapsedChange?: (collapsed: boolean) => void
}

export default function Sidebar({ currentPage, onNavigate, onCollapsedChange }: SidebarProps) {
  // Load collapsed state from localStorage
  const [isCollapsed, setIsCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebar-collapsed')
    return saved === 'true'
  })
  const [isMobileOpen, setIsMobileOpen] = useState(false)

  // Save collapsed state to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('sidebar-collapsed', isCollapsed.toString())
    onCollapsedChange?.(isCollapsed)
  }, [isCollapsed, onCollapsedChange])

  // Notify parent on mount
  useEffect(() => {
    onCollapsedChange?.(isCollapsed)
  }, [])

  const navigation = [
    { name: 'All Orders', icon: HomeIcon, id: 'orders' },
    { name: 'Analytics', icon: ChartBarIcon, id: 'analytics' },
    { name: 'Settings', icon: Cog6ToothIcon, id: 'settings' },
  ]

  return (
    <>
      {/* Mobile menu button */}
      <div className="lg:hidden fixed top-4 left-4 z-50">
        <button
          onClick={() => setIsMobileOpen(!isMobileOpen)}
          className="inline-flex items-center justify-center p-2 rounded-md text-gray-700 bg-white shadow-md hover:bg-gray-100 focus:outline-none"
        >
          {isMobileOpen ? (
            <XMarkIcon className="h-6 w-6" />
          ) : (
            <Bars3Icon className="h-6 w-6" />
          )}
        </button>
      </div>

      {/* Mobile sidebar overlay */}
      {isMobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-gray-600 bg-opacity-75 z-40"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div
        className={`
          fixed inset-y-0 left-0 z-40 bg-white border-r border-gray-200 transform transition-all duration-300 ease-in-out
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full'}
          lg:translate-x-0
          ${isCollapsed ? 'lg:w-20' : 'lg:w-64'}
        `}
      >
        <div className="flex flex-col h-full">
          {/* Logo/Header */}
          <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200">
            {isCollapsed ? (
              <div className="flex items-center justify-center w-full">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">R</span>
                </div>
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">R</span>
                </div>
                <div className="flex flex-col">
                  <span className="font-bold text-gray-900">ROMS V2</span>
                  <span className="text-xs text-gray-500">Order Management</span>
                </div>
              </div>
            )}
            
            {/* Collapse button (desktop only) */}
            {!isCollapsed && (
              <button
                onClick={() => setIsCollapsed(!isCollapsed)}
                className="hidden lg:block p-1.5 rounded-md hover:bg-gray-100 text-gray-500"
              >
                <ChevronLeftIcon className="h-5 w-5" />
              </button>
            )}
          </div>
          
          {/* Expand button when collapsed */}
          {isCollapsed && (
            <div className="hidden lg:flex justify-center py-2 border-b border-gray-200">
              <button
                onClick={() => setIsCollapsed(!isCollapsed)}
                className="p-1.5 rounded-md hover:bg-gray-100 text-gray-500"
                title="Expand sidebar"
              >
                <ChevronRightIcon className="h-5 w-5" />
              </button>
            </div>
          )}

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = currentPage === item.id
              
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    onNavigate(item.id)
                    setIsMobileOpen(false)
                  }}
                  className={`
                    w-full flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-colors
                    ${isActive
                      ? 'bg-blue-50 text-blue-600'
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    }
                    ${isCollapsed ? 'justify-center' : ''}
                  `}
                  title={isCollapsed ? item.name : undefined}
                >
                  <Icon className={`h-5 w-5 flex-shrink-0 ${!isCollapsed && 'mr-3'}`} />
                  {!isCollapsed && <span>{item.name}</span>}
                </button>
              )
            })}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200">
            <div className={`flex items-center ${isCollapsed ? 'justify-center' : 'space-x-3'}`}>
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              {!isCollapsed && (
                <div className="flex-1">
                  <p className="text-xs font-medium text-gray-900">System Online</p>
                  <p className="text-xs text-gray-500">V2.0.0</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

