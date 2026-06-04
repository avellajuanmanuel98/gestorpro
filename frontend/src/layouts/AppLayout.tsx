import { useState } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Users, FileText, Building2, LogOut,
  Menu, X, UserCheck, Truck, BarChart2, Boxes,
  Moon, Sun, ChevronRight, Bell,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useThemeStore } from '@/store/themeStore'

// ── Navigation config ─────────────────────────────────────────────────────────

const navGroups = [
  {
    label: 'Principal',
    items: [
      { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard'   },
      { to: '/clients',   icon: Users,           label: 'Clientes'    },
      { to: '/invoices',  icon: FileText,        label: 'Facturación' },
      { to: '/inventory', icon: Boxes,           label: 'Inventario'  },
    ],
  },
  {
    label: 'Recursos',
    items: [
      { to: '/employees', icon: UserCheck, label: 'Empleados'   },
      { to: '/suppliers', icon: Truck,     label: 'Proveedores' },
      { to: '/reports',   icon: BarChart2, label: 'Reportes'    },
    ],
  },
  {
    label: 'Configuración',
    items: [
      { to: '/company', icon: Building2, label: 'Mi Empresa' },
    ],
  },
]

// Labels for the page header breadcrumb
const routeLabels: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/clients':   'Clientes',
  '/invoices':  'Facturación',
  '/inventory': 'Inventario',
  '/employees': 'Empleados',
  '/suppliers': 'Proveedores',
  '/reports':   'Reportes',
  '/company':   'Mi Empresa',
}

// ── Avatar ────────────────────────────────────────────────────────────────────

function Avatar({ name, size = 'sm' }: { name?: string; size?: 'sm' | 'md' }) {
  const initials = name
    ? name
        .split(' ')
        .slice(0, 2)
        .map((n) => n[0])
        .join('')
        .toUpperCase()
    : '?'

  const sizeClass = size === 'md' ? 'w-9 h-9 text-sm' : 'w-7 h-7 text-xs'

  return (
    <div
      className={[
        sizeClass,
        'rounded-full flex items-center justify-center font-semibold shrink-0',
        'bg-gradient-to-br from-indigo-500 to-violet-600 text-white',
        'ring-2 ring-white dark:ring-zinc-900 shadow-sm',
      ].join(' ')}
    >
      {initials}
    </div>
  )
}

// ── Sidebar content ───────────────────────────────────────────────────────────

function SidebarContent({ onNavClick }: { onNavClick?: () => void }) {
  const { user, logout }   = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex flex-col h-full">

      {/* ── Logo ── */}
      <div className="h-14 flex items-center px-5 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-sm shadow-indigo-500/30">
            <span className="text-white text-xs font-bold">G</span>
          </div>
          <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 tracking-tight">
            GestorPro
          </span>
        </div>
      </div>

      {/* ── Navigation ── */}
      <nav className="flex-1 overflow-y-auto px-3 pb-4 space-y-5">
        {navGroups.map((group) => (
          <div key={group.label}>
            <p className="px-2.5 mb-1 text-[10px] font-semibold tracking-widest uppercase text-zinc-400 dark:text-zinc-600">
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.items.map(({ to, icon: Icon, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={onNavClick}
                  className={({ isActive }) =>
                    [
                      'relative flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm font-medium',
                      'transition-all duration-150 group',
                      isActive
                        ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-400 nav-item-active'
                        : 'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900 dark:text-zinc-400 dark:hover:bg-zinc-800/80 dark:hover:text-zinc-100',
                    ].join(' ')
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon
                        size={16}
                        className={[
                          'shrink-0 transition-colors',
                          isActive
                            ? 'text-indigo-600 dark:text-indigo-400'
                            : 'text-zinc-400 group-hover:text-zinc-600 dark:group-hover:text-zinc-300',
                        ].join(' ')}
                      />
                      <span className="truncate">{label}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* ── Bottom: user + theme toggle ── */}
      <div className="shrink-0 border-t border-zinc-200 dark:border-zinc-800 p-3 space-y-1">

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className={[
            'w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm font-medium',
            'text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900',
            'dark:text-zinc-400 dark:hover:bg-zinc-800/80 dark:hover:text-zinc-100',
            'transition-all duration-150',
          ].join(' ')}
        >
          {theme === 'dark' ? (
            <Sun size={16} className="text-zinc-400 shrink-0" />
          ) : (
            <Moon size={16} className="text-zinc-400 shrink-0" />
          )}
          <span>{theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}</span>
        </button>

        {/* User card */}
        <div className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800/80 transition-colors cursor-default group">
          <Avatar name={user?.full_name} size="sm" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate leading-none mb-0.5">
              {user?.full_name ?? 'Usuario'}
            </p>
            <p className="text-xs text-zinc-500 dark:text-zinc-500 truncate">
              {user?.email}
            </p>
          </div>
          <button
            onClick={handleLogout}
            title="Cerrar sesión"
            className={[
              'p-1 rounded-md opacity-0 group-hover:opacity-100 transition-all',
              'text-zinc-400 hover:text-red-600 hover:bg-red-50',
              'dark:hover:text-red-400 dark:hover:bg-red-950/40',
            ].join(' ')}
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main Layout ───────────────────────────────────────────────────────────────

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  const user = useAuthStore((s) => s.user)

  const currentLabel = routeLabels[location.pathname] ?? 'GestorPro'

  return (
    <div className="flex h-screen bg-zinc-50 dark:bg-zinc-950 overflow-hidden transition-colors duration-300">

      {/* ── Desktop sidebar ── */}
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 transition-colors duration-300">
        <SidebarContent />
      </aside>

      {/* ── Mobile drawer ── */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fade-in"
            onClick={() => setSidebarOpen(false)}
          />
          {/* Panel */}
          <aside className="animate-slide-left absolute left-0 top-0 h-full w-64 bg-white dark:bg-zinc-950 border-r border-zinc-200 dark:border-zinc-800 flex flex-col shadow-2xl">
            <div className="absolute top-3 right-3">
              <button
                onClick={() => setSidebarOpen(false)}
                className="p-1.5 rounded-lg text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
              >
                <X size={16} />
              </button>
            </div>
            <SidebarContent onNavClick={() => setSidebarOpen(false)} />
          </aside>
        </div>
      )}

      {/* ── Main content ── */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">

        {/* ── Top header ── */}
        <header className="h-14 shrink-0 bg-white dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800 flex items-center px-4 md:px-6 gap-3 transition-colors duration-300">

          {/* Mobile hamburger */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="md:hidden p-1.5 rounded-lg text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
          >
            <Menu size={18} />
          </button>

          {/* Breadcrumb */}
          <div className="flex items-center gap-1.5 text-sm">
            <span className="hidden md:block text-zinc-400 dark:text-zinc-600 font-medium">GestorPro</span>
            <ChevronRight size={14} className="hidden md:block text-zinc-300 dark:text-zinc-700" />
            <span className="font-semibold text-zinc-900 dark:text-zinc-100">{currentLabel}</span>
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* Right actions */}
          <div className="flex items-center gap-2">
            {/* Notifications bell (placeholder) */}
            <button className="relative p-2 rounded-lg text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700 dark:hover:bg-zinc-800 dark:hover:text-zinc-300 transition-colors">
              <Bell size={16} />
              <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-indigo-500 rounded-full" />
            </button>

            {/* Avatar (desktop only) */}
            <div className="hidden md:block">
              <Avatar name={user?.full_name} size="sm" />
            </div>
          </div>
        </header>

        {/* ── Page content ── */}
        <main className="flex-1 overflow-auto">
          <div className="page-enter">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
