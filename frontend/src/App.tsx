import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore, useCan, useHasFeature } from '@/store/authStore'
import AssistantButton from '@/components/ai/AssistantButton'
import Toaster from '@/components/ui/Toaster'

// Páginas
import LoginPage       from '@/pages/auth/LoginPage'
import RegisterPage    from '@/pages/auth/RegisterPage'
import DashboardPage   from '@/pages/dashboard/DashboardPage'
import ClientsPage     from '@/pages/clients/ClientsPage'
import InvoicesPage    from '@/pages/billing/InvoicesPage'
import CompanyPage     from '@/pages/settings/CompanyPage'
import EmployeesPage   from '@/pages/employees/EmployeesPage'
import SuppliersPage   from '@/pages/suppliers/SuppliersPage'
import ReportsPage     from '@/pages/reports/ReportsPage'
import InventoryPage   from '@/pages/inventory/InventoryPage'
import IngredientsPage from '@/pages/inventory/IngredientsPage'
import UsersPage       from '@/pages/access/UsersPage'
import RolesPage       from '@/pages/access/RolesPage'
import AuditPage       from '@/pages/access/AuditPage'
import AcceptInvitationPage from '@/pages/auth/AcceptInvitationPage'

// Layout principal con sidebar
import AppLayout from '@/layouts/AppLayout'

// Componente que protege rutas — si no estás logueado, te manda al login
function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function App() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const refreshSession  = useAuthStore((s) => s.refreshSession)
  const can = useCan()
  const hasFeature = useHasFeature()
  const canUseAssistant = can('assistant.use') && hasFeature('module.assistant')

  // Al abrir la app, la sesión (empresa activa, rol y permisos) se vuelve a
  // pedir al servidor: lo guardado en el navegador puede estar desactualizado.
  useEffect(() => {
    if (isAuthenticated) void refreshSession().catch(() => undefined)
  }, [isAuthenticated, refreshSession])

  return (
    <>
      <Routes>
        {/* Rutas públicas */}
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/invitation/:token" element={<AcceptInvitationPage />} />

        {/* Rutas protegidas — todas dentro del AppLayout (sidebar + header) */}
        <Route
          path="/"
          element={
            <PrivateRoute>
              <AppLayout />
            </PrivateRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="clients"   element={<ClientsPage />} />
          <Route path="invoices"  element={<InvoicesPage />} />
          <Route path="inventory" element={<InventoryPage />} />
          <Route path="ingredients" element={<IngredientsPage />} />
          <Route path="employees" element={<EmployeesPage />} />
          <Route path="suppliers" element={<SuppliersPage />} />
          <Route path="reports"   element={<ReportsPage />} />
          <Route path="company"   element={<CompanyPage />} />
          <Route path="users"     element={<UsersPage />} />
          <Route path="roles"     element={<RolesPage />} />
          <Route path="audit"     element={<AuditPage />} />
        </Route>

        {/* Cualquier ruta desconocida → dashboard */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>

      {/* Asistente IA — solo si el rol lo incluye (el backend también lo exige) */}
      {isAuthenticated && canUseAssistant && <AssistantButton />}
      <Toaster />
    </>
  )
}

export default App
