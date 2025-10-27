import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import Sidebar from './components/Sidebar'
import AllOrders from './pages/AllOrders'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000,
    },
  },
})

function App() {
  const [currentPage, setCurrentPage] = useState('orders')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebar-collapsed')
    return saved === 'true'
  })

  const renderPage = () => {
    switch (currentPage) {
      case 'orders':
        return <AllOrders />
      case 'analytics':
        return <Analytics />
      case 'settings':
        return <Settings />
      default:
        return <AllOrders />
    }
  }

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-50 flex" style={{ width: '100vw', maxWidth: '100vw', overflow: 'hidden' }}>
        <Sidebar 
          currentPage={currentPage} 
          onNavigate={setCurrentPage}
          onCollapsedChange={setSidebarCollapsed}
        />
        <main 
          className={`flex-1 transition-all duration-300 ${sidebarCollapsed ? 'lg:ml-20' : 'lg:ml-64'}`}
          style={{ 
            maxWidth: '100%', 
            overflow: 'hidden'
          }}
        >
          {renderPage()}
        </main>
      </div>
    </QueryClientProvider>
  )
}

export default App

