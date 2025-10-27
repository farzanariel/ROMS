import { NavLink } from 'react-router-dom'
import {
  HomeIcon,
  ClockIcon,
  DocumentTextIcon,
  CogIcon,
  ChartBarIcon,
  SunIcon,
  MoonIcon,
  ArrowUpTrayIcon
} from '@heroicons/react/24/outline'
import { useDarkMode } from '../contexts/DarkModeContext'

const navigation = [
  { name: 'Dashboard', href: '/', icon: HomeIcon },
  { name: 'Analytics', href: '/analytics', icon: ChartBarIcon },
  { name: 'Pending', href: '/pending', icon: ClockIcon },
  { name: 'All Orders', href: '/orders', icon: DocumentTextIcon },
  { name: 'Actions', href: '/actions', icon: ArrowUpTrayIcon },
  { name: 'Settings', href: '/settings', icon: CogIcon },
]

export default function BottomNavigation() {
  const { isDarkMode, toggleDarkMode } = useDarkMode()
  
  return (
    <div className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 shadow-lg">
      <div className="flex items-center justify-around px-2 py-2">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              `flex flex-col items-center px-3 py-2 text-xs font-medium rounded-md transition-colors duration-200 ${
                isActive
                  ? 'text-primary-700 dark:text-primary-300 bg-primary-100 dark:bg-primary-800/40 border border-primary-200 dark:border-primary-600'
                  : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100'
              }`
            }
          >
            <item.icon className="h-5 w-5 mb-1" />
            <span>{item.name}</span>
          </NavLink>
        ))}
        
        {/* Dark mode toggle */}
        <button
          onClick={toggleDarkMode}
          className="flex flex-col items-center px-3 py-2 text-xs font-medium text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
        >
          {isDarkMode ? (
            <>
              <SunIcon className="h-5 w-5 mb-1 text-primary-600 dark:text-primary-400" />
              <span>Light</span>
            </>
          ) : (
            <>
              <MoonIcon className="h-5 w-5 mb-1 text-primary-600 dark:text-primary-400" />
              <span>Dark</span>
            </>
          )}
        </button>
      </div>
    </div>
  )
}
