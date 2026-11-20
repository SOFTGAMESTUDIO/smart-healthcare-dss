import React, { Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Navbar from './components/Navbar'

// ── Lazy-loaded pages ─────────────────────────────────────────────────────────
const LoginPage         = lazy(() => import('./pages/LoginPage'))
const DashboardPage     = lazy(() => import('./pages/DashboardPage'))
const PatientsPage      = lazy(() => import('./pages/PatientsPage'))
const NewPatientPage    = lazy(() => import('./pages/NewPatientPage'))
const PatientDetailPage = lazy(() => import('./pages/PatientDetailPage'))
const AppointmentsPage  = lazy(() => import('./pages/AppointmentsPage'))
const SchedulePage      = lazy(() => import('./pages/SchedulePage'))
const SimulationPage    = lazy(() => import('./pages/SimulationPage'))
const AIDiagnosisPage   = lazy(() => import('./pages/AIDiagnosisPage'))
const ResearchPage      = lazy(() => import('./pages/ResearchPage'))

// ── Page-level loading fallback ───────────────────────────────────────────────
function PageSpinner() {
  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-slate-500">Loading…</p>
      </div>
    </div>
  )
}

// ── Protected route wrapper ───────────────────────────────────────────────────
/**
 * Renders children only when authenticated.
 * While the session is being restored from localStorage it shows a spinner.
 * Unauthenticated visitors are redirected to /login.
 */
function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth()

  if (loading) return <PageSpinner />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <Outlet />
}

// ── App layout (Navbar + routed content) ─────────────────────────────────────
function AppLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Navbar />
      <main className="flex-1 container mx-auto px-4 py-6 max-w-7xl">
        <Suspense fallback={<PageSpinner />}>
          <Outlet />
        </Suspense>
      </main>
      <footer className="text-center text-xs text-slate-400 py-3 border-t border-slate-100">
        XAI Healthcare DSS &copy; {new Date().getFullYear()}
      </footer>
    </div>
  )
}

// ── Root router ───────────────────────────────────────────────────────────────
function AppRoutes() {
  const { isAuthenticated, loading } = useAuth()

  return (
    <Routes>
      {/* Public */}
      <Route
        path="/login"
        element={
          <Suspense fallback={<PageSpinner />}>
            {!loading && isAuthenticated ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <LoginPage />
            )}
          </Suspense>
        }
      />

      {/* Root redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* Protected routes wrapped in AppLayout */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard"       element={<DashboardPage />} />
          <Route path="/patients"        element={<PatientsPage />} />
          <Route path="/patients/new"    element={<NewPatientPage />} />
          <Route path="/patients/:id"    element={<PatientDetailPage />} />
          <Route path="/appointments"    element={<AppointmentsPage />} />
          <Route path="/schedule"        element={<SchedulePage />} />
          <Route path="/simulation"      element={<SimulationPage />} />
          <Route path="/ai-diagnosis"    element={<AIDiagnosisPage />} />
          <Route path="/research"        element={<ResearchPage />} />
        </Route>
      </Route>

      {/* 404 fallback */}
      <Route
        path="*"
        element={
          <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
            <h1 className="text-5xl font-bold text-slate-300">404</h1>
            <p className="text-slate-500">Page not found.</p>
            <a
              href="/dashboard"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
            >
              Go to Dashboard
            </a>
          </div>
        }
      />
    </Routes>
  )
}

// ── Navbar component (inline — full component in components/Navbar.jsx) ───────
// App.jsx just wires everything; Navbar is imported from components/Navbar.jsx

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
