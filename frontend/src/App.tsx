import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore, useCan, useHasFeature, useHasModule } from '@/store/authStore'
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
import PosPage         from '@/pages/pos/PosPage'
import CashPage        from '@/pages/cash/CashPage'
import SalesPage       from '@/pages/sales/SalesPage'
import PurchasesPage   from '@/pages/purchases/PurchasesPage'
import RecipesPage     from '@/pages/production/RecipesPage'
import ProductionPage  from '@/pages/production/ProductionPage'
import WastePage       from '@/pages/waste/WastePage'
import MovementsPage   from '@/pages/inventory/MovementsPage'
import UsersPage       from '@/pages/access/UsersPage'
import RolesPage       from '@/pages/access/RolesPage'
import AuditPage       from '@/pages/access/AuditPage'
import AcceptInvitationPage from '@/pages/auth/AcceptInvitationPage'

// Layout principal con sidebar
import AppLayout from '@/layouts/AppLayout'
import PlatformLayout from '@/layouts/PlatformLayout'
import PlatformOverviewPage from '@/pages/platform/PlatformOverviewPage'
import PlatformTenantsPage from '@/pages/platform/PlatformTenantsPage'
import PlatformTenantDetailPage from '@/pages/platform/PlatformTenantDetailPage'
import PlatformPlansPage from '@/pages/platform/PlatformPlansPage'
import PlatformEventsPage from '@/pages/platform/PlatformEventsPage'

/** Quien vende y no ve métricas (cajero) entra directo al POS; el resto, al inicio. */
/** Módulo apagado para esta empresa (p. ej. producción en una lavandería): no se muestra la pantalla. */
function RequireModule({ module, children }: { module: string; children: React.ReactNode }) {
  const hasModule = useHasModule()
  return hasModule(module) ? <>{children}</> : <Navigate to="/dashboard" replace />
}

function HomeRedirect() {
  const can = useCan()
  const session = useAuthStore((s) => s.session)
  if (session && !session.tenant && session.user.is_platform_admin) return <Navigate to="/platform" replace />
  return <Navigate to={can('sales.sell') && !can('reports.view') ? '/pos' : '/dashboard'} replace />
}

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
          <Route index element={<HomeRedirect />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="clients"   element={<ClientsPage />} />
          <Route path="invoices"  element={<InvoicesPage />} />
          <Route path="inventory" element={<InventoryPage />} />
          <Route path="ingredients" element={<IngredientsPage />} />
          <Route path="pos"       element={<PosPage />} />
          <Route path="cash"      element={<CashPage />} />
          <Route path="sales"     element={<SalesPage />} />
          <Route path="purchases" element={<PurchasesPage />} />
          <Route path="recipes"   element={<RequireModule module="production"><RecipesPage /></RequireModule>} />
          <Route path="production" element={<RequireModule module="production"><ProductionPage /></RequireModule>} />
          <Route path="waste"     element={<RequireModule module="waste"><WastePage /></RequireModule>} />
          <Route path="movements" element={<MovementsPage />} />
          <Route path="employees" element={<EmployeesPage />} />
          <Route path="suppliers" element={<SuppliersPage />} />
          <Route path="reports"   element={<ReportsPage />} />
          <Route path="company"   element={<CompanyPage />} />
          <Route path="users"     element={<UsersPage />} />
          <Route path="roles"     element={<RolesPage />} />
          <Route path="audit"     element={<AuditPage />} />
        </Route>

        {/* Consola de la plataforma (personal de GestorPro) */}
        <Route path="/platform" element={<PrivateRoute><PlatformLayout /></PrivateRoute>}>
          <Route index element={<PlatformOverviewPage />} />
          <Route path="tenants" element={<PlatformTenantsPage />} />
          <Route path="tenants/:id" element={<PlatformTenantDetailPage />} />
          <Route path="plans" element={<PlatformPlansPage />} />
          <Route path="events" element={<PlatformEventsPage />} />
        </Route>

        {/* Cualquier ruta desconocida → dashboard */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      {/* Asistente IA — solo si el rol lo incluye (el backend también lo exige) */}
      {isAuthenticated && canUseAssistant && <AssistantButton />}
      <Toaster />
    </>
  )
}

export default App
