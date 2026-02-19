import { Routes, Route, Navigate } from 'react-router-dom'
// import { ProtectedRoute } from './components/auth/ProtectedRoute'
// import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage' // NEW
import { SearchPage } from './pages/SearchPage'       // NEW
import { DataExplorerPage } from './pages/DataExplorerPage' // NEW
import { AdminPage } from './pages/AdminPage'
import { Layout } from './components/layout/Layout'
import { ErrorTester } from './components/debug/ErrorTester'

const isDevelopment = import.meta.env.VITE_ENVIRONMENT === 'development'

function App() {
  return (
    <Routes>
      {/* <Route path="/login" element={<LoginPage />} /> */}
      <Route
        path="/"
        element={
          // <ProtectedRoute>
            <DashboardPage />
          // </ProtectedRoute>
        }
      />
      <Route
        path="/search"
        element={
          // <ProtectedRoute>
            <SearchPage />
          // </ProtectedRoute>
        }
      />
      <Route
        path="/explorer"
        element={
          // <ProtectedRoute>
            <DataExplorerPage />
          // </ProtectedRoute>
        }
      />
      <Route path="/explorer" element={<DataExplorerPage />} />
      <Route
        path="/admin"
        element={
          // <ProtectedRoute requireRole="admin">
            <AdminPage />
          // </ProtectedRoute>
        }
      />
      {isDevelopment && (
        <Route
          path="/error-test"
          element={
            // <ProtectedRoute>
              <Layout>
                <ErrorTester />
              </Layout>
            // </ProtectedRoute>
          }
        />
      )}
      <Route path="/*" element={<Navigate to="/" />} />
    </Routes>
  )
}

export default App
