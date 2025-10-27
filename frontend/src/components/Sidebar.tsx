import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import {
  HomeIcon,
  ClockIcon,
  DocumentTextIcon,
  CogIcon,
  ChartBarIcon,
  SunIcon,
  MoonIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ArrowUpTrayIcon
} from '@heroicons/react/24/outline'
import { useDarkMode } from '../contexts/DarkModeContext'

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Analytics', href: '/analytics', icon: ChartBarIcon },
  { name: 'Pending Orders', href: '/pending', icon: ClockIcon },
  { name: 'All Orders', href: '/orders', icon: DocumentTextIcon },
  { name: 'Actions', href: '/actions', icon: ArrowUpTrayIcon },
  { name: 'Settings', href: '/settings', icon: CogIcon },
]

export default function Sidebar() {
  const { isDarkMode, toggleDarkMode } = useDarkMode()
  const [isCollapsed, setIsCollapsed] = useState(false)
  
  console.log('🔄 Sidebar render - isCollapsed:', isCollapsed, 'icon sizes:', isCollapsed ? 'h-12 w-12' : 'h-8 w-8')
  
  // Force re-render when state changes
  useEffect(() => {
    console.log('🔄 Sidebar state changed to:', isCollapsed)
  }, [isCollapsed])
  
  return (
    <div className={`hidden lg:block bg-white dark:bg-gray-800 shadow-sm border-r border-gray-200 dark:border-gray-700 transition-all duration-300 ease-in-out ${
      isCollapsed ? 'w-16' : 'w-64'
    }`}>
      <div className="flex flex-col h-full">
                            {/* Logo and Toggle */}
                    <div className="flex items-center justify-between px-4 py-4 border-b border-gray-200 dark:border-gray-700">
                      <div className="flex items-center">
                        {isCollapsed ? (
                          <button
                            onClick={() => setIsCollapsed(!isCollapsed)}
                            className="p-1 rounded-md text-gray-600 dark:text-gray-200 hover:text-gray-800 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                          >
                            <ChevronRightIcon className="h-6 w-6" />
                          </button>
                        ) : (
                          <>
                            <ChartBarIcon 
                              className="h-8 w-8 text-primary-500 dark:text-primary-300" 
                            />
                            <h1 className="ml-3 text-xl font-bold text-gray-900 dark:text-gray-100">Order Dashboard</h1>
                          </>
                        )}
                      </div>

                      {/* Toggle Button - Only show when expanded */}
                      {!isCollapsed && (
                        <button
                          onClick={() => setIsCollapsed(!isCollapsed)}
                          className="p-1 rounded-md text-gray-600 dark:text-gray-200 hover:text-gray-800 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                        >
                          <ChevronLeftIcon className="h-5 w-5" />
                        </button>
                      )}
                    </div>

        {/* Navigation */}
        <nav className={`flex-1 py-6 space-y-2 ${isCollapsed ? 'px-2' : 'px-4'}`}>
          {navigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) =>
                `flex items-center text-sm font-medium rounded-md transition-colors duration-200 ${
                  isCollapsed 
                    ? 'px-2 py-3 justify-center' 
                    : 'px-3 py-2 justify-start'
                } ${
                  isActive
                    ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                    : 'text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-gray-100'
                }`
              }
              title={isCollapsed ? item.name : undefined}
            >
              {({ isActive }) => (
                <>
                  <item.icon 
                    className={`${isCollapsed ? 'h-6 w-6' : 'h-5 w-5 mr-3'} ${
                      isActive 
                        ? 'text-gray-900 dark:text-gray-100' 
                        : 'text-gray-600 dark:text-gray-300'
                    }`}
                    style={{
                      width: isCollapsed ? '1.5rem' : '1.25rem',
                      height: isCollapsed ? '1.5rem' : '1.25rem',
                      minWidth: isCollapsed ? '1.5rem' : '1.25rem',
                      minHeight: isCollapsed ? '1.5rem' : '1.25rem'
                    }}
                  />
                  {!isCollapsed && <span>{item.name}</span>}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className={`border-t border-gray-200 dark:border-gray-700 ${
          isCollapsed ? 'px-2 py-4' : 'px-6 py-4'
        }`}>
          <div className="flex items-center justify-between">
            {!isCollapsed && (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Order Management v1.0
              </p>
            )}
            <button
              onClick={toggleDarkMode}
              className={`text-gray-600 dark:text-gray-200 hover:text-gray-800 dark:hover:text-white transition-colors ${
                isCollapsed ? 'mx-auto p-2' : 'p-2'
              }`}
              title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {isDarkMode ? (
                <SunIcon className={`${isCollapsed ? 'h-6 w-6' : 'h-4 w-4'}`} />
              ) : (
                <MoonIcon className={`${isCollapsed ? 'h-6 w-6' : 'h-4 w-4'}`} />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
