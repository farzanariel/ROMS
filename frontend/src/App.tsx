import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import { DarkModeProvider } from './contexts/DarkModeContext'
import Sidebar from './components/Sidebar'
import BottomNavigation from './components/BottomNavigation'
import Dashboard from './pages/Dashboard'
import PendingOrders from './pages/PendingOrders'
import AllOrders from './pages/AllOrders'
import Settings from './pages/Settings'
import Actions from './pages/Actions'
import Analytics from './pages/Analytics'

function App() {
  const [sheetUrl, setSheetUrl] = useState(
    localStorage.getItem('sheetUrl') || ''
  )

  const updateSheetUrl = (url: string) => {
    setSheetUrl(url)
    localStorage.setItem('sheetUrl', url)
  }

                return (
                <DarkModeProvider>
                  <div className="flex h-screen bg-gray-100 dark:bg-gray-900">
                    <Sidebar />
                    <main className="flex-1 overflow-y-auto min-w-0">
                      <Routes>
                        <Route 
                          path="/" 
                          element={<Dashboard sheetUrl={sheetUrl} />} 
                        />
                        <Route 
                          path="/pending" 
                          element={<PendingOrders sheetUrl={sheetUrl} />} 
                        />
                        <Route 
                          path="/orders" 
                          element={<AllOrders sheetUrl={sheetUrl} />} 
                        />
                        <Route 
                          path="/settings" 
                          element={<Settings sheetUrl={sheetUrl} onSheetUrlChange={updateSheetUrl} />} 
                        />
                        <Route
                          path="/actions"
                          element={<Actions sheetUrl={sheetUrl} />}
                        />
                        <Route
                          path="/analytics"
                          element={<Analytics sheetUrl={sheetUrl} />}
                        />
                      </Routes>
                    </main>
                  </div>
                  <BottomNavigation />
                </DarkModeProvider>
              )
            }

export default App
