import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import { reportsApi } from '@/api/reports'
import { AlertTriangle, Package, Users, Truck } from 'lucide-react'

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatCurrency(v: number) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency', currency: 'COP', minimumFractionDigits: 0,
  }).format(v)
}

function formatCompact(v: number) {
  return new Intl.NumberFormat('es-CO', {
    notation: 'compact', maximumFractionDigits: 1,
  }).format(v)
}

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899']

function CustomTooltipCurrency({ active, payload, label }: any) {
  if (active && payload?.length) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-4 py-2 text-sm">
        <p className="font-semibold text-gray-700">{label}</p>
        <p className="text-indigo-600">{formatCurrency(payload[0].value)}</p>
      </div>
    )
  }
  return null
}

function CustomTooltipCount({ active, payload, label }: any) {
  if (active && payload?.length) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-4 py-2 text-sm">
        <p className="font-semibold text-gray-700">{label}</p>
        <p className="text-indigo-600">{payload[0].value} {payload[0].name}</p>
      </div>
    )
  }
  return null
}

function EmptyState({ text }: { text: string }) {
  return <p className="text-sm text-gray-400 text-center py-10">{text}</p>
}

function Spinner() {
  return (
    <div className="flex justify-center py-16">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
    </div>
  )
}

// ── Tabs ─────────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'billing',   label: 'Facturación' },
  { id: 'inventory', label: 'Inventario'  },
  { id: 'hr',        label: 'RRHH & Proveedores' },
] as const

type TabId = typeof TABS[number]['id']

// ── Tab: Facturación ──────────────────────────────────────────────────────────

function BillingTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['report-billing'],
    queryFn: reportsApi.billing,
  })

  if (isLoading) return <Spinner />

  const STATUS_COLORS: Record<string, string> = {
    paid: '#22c55e', sent: '#6366f1', draft: '#9ca3af',
    overdue: '#ef4444', cancelled: '#d1d5db',
  }

  return (
    <div className="space-y-8">
      {/* Tendencia mensual */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="font-semibold text-gray-900 mb-1">Ventas mensuales (últimos 12 meses)</h3>
        <p className="text-sm text-gray-500 mb-6">Facturas con estado "Pagada"</p>
        {!data?.monthly_trend.length ? <EmptyState text="Sin ventas registradas aún" /> : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.monthly_trend} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="mes" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={formatCompact} tick={{ fontSize: 12 }} width={64} />
              <Tooltip content={<CustomTooltipCurrency />} />
              <Bar dataKey="total" name="Total" fill="#6366f1" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Desglose por estado — Pie chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-1">Estado de facturas</h3>
          <p className="text-sm text-gray-500 mb-4">Distribución por estado actual</p>
          {!data?.status_breakdown.length ? <EmptyState text="Sin facturas aún" /> : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={data.status_breakdown}
                  dataKey="count"
                  nameKey="label"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name, value }: any) => `${name} (${value})`}
                  labelLine={false}
                >
                  {data.status_breakdown.map((entry) => (
                    <Cell
                      key={entry.status}
                      fill={STATUS_COLORS[entry.status] ?? '#9ca3af'}
                    />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => [`${v} facturas`]} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Top 5 clientes */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-1">Top clientes por ingreso</h3>
          <p className="text-sm text-gray-500 mb-4">Facturas pagadas acumuladas</p>
          {!data?.top_clients.length ? <EmptyState text="Sin datos de clientes aún" /> : (
            <div className="space-y-3">
              {data.top_clients.map((client, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-600 text-xs font-bold flex items-center justify-center shrink-0">
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{client.name}</p>
                    <p className="text-xs text-gray-500">{client.count} factura{client.count !== 1 ? 's' : ''}</p>
                  </div>
                  <span className="text-sm font-semibold text-green-600 shrink-0">
                    {formatCurrency(client.total)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Tab: Inventario ───────────────────────────────────────────────────────────

function InventoryTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['report-inventory'],
    queryFn: reportsApi.inventory,
  })

  if (isLoading) return <Spinner />

  return (
    <div className="space-y-8">
      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: 'Productos activos',  value: data?.total_productos ?? 0,                    icon: Package,       color: 'bg-indigo-500' },
          { label: 'Servicios activos',  value: data?.total_servicios ?? 0,                    icon: Users,         color: 'bg-purple-500' },
          { label: 'Valor inventario',   value: formatCurrency(data?.valor_inventario ?? 0),   icon: Package,       color: 'bg-green-500'  },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-5 flex items-center gap-4">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
              <Icon size={18} className="text-white" />
            </div>
            <div>
              <p className="text-xs text-gray-500">{label}</p>
              <p className="text-xl font-bold text-gray-900">{value}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Stock por categoría */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-1">Stock por categoría</h3>
          <p className="text-sm text-gray-500 mb-4">Unidades disponibles agrupadas</p>
          {!data?.by_category.length ? <EmptyState text="Sin productos categorizados" /> : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={data.by_category} layout="vertical" margin={{ top: 4, right: 24, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="categoria" tick={{ fontSize: 12 }} width={100} />
                <Tooltip content={<CustomTooltipCount />} />
                <Bar dataKey="stock" name="unidades" fill="#6366f1" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Productos con bajo stock */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-1 flex items-center gap-2">
            <AlertTriangle size={16} className="text-amber-500" />
            Bajo stock
          </h3>
          <p className="text-sm text-gray-500 mb-4">Productos en o por debajo del mínimo</p>
          {!data?.low_stock.length ? (
            <p className="text-sm text-green-600 text-center py-10">✓ Todo el stock está en niveles saludables</p>
          ) : (
            <div className="space-y-3">
              {data.low_stock.map((p, i) => (
                <div key={i} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{p.name}</p>
                    <p className="text-xs text-gray-400">{p.code}</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-sm font-bold ${p.stock === 0 ? 'text-red-600' : 'text-amber-600'}`}>
                      {p.stock} uds
                    </p>
                    <p className="text-xs text-gray-400">mín. {p.minimum_stock}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Tab: RRHH & Proveedores ───────────────────────────────────────────────────

function HRTab() {
  const { data, isLoading } = useQuery({
    queryKey: ['report-hr'],
    queryFn: reportsApi.hr,
  })

  if (isLoading) return <Spinner />

  const empTotal = (data?.employees_active ?? 0) + (data?.employees_inactive ?? 0)
  const empPieData = [
    { name: 'Activos',   value: data?.employees_active   ?? 0, fill: '#22c55e' },
    { name: 'Inactivos', value: data?.employees_inactive ?? 0, fill: '#9ca3af' },
  ].filter(d => d.value > 0)

  return (
    <div className="space-y-8">
      {/* KPIs empleados */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: 'Total empleados', value: empTotal,                          color: 'bg-indigo-500', icon: Users },
          { label: 'Activos',         value: data?.employees_active ?? 0,        color: 'bg-green-500', icon: Users },
          { label: 'Proveedores',     value: (data?.suppliers_by_category ?? []).reduce((s, c) => s + c.total, 0), color: 'bg-amber-500', icon: Truck },
        ].map(({ label, value, color, icon: Icon }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-5 flex items-center gap-4">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
              <Icon size={18} className="text-white" />
            </div>
            <div>
              <p className="text-xs text-gray-500">{label}</p>
              <p className="text-xl font-bold text-gray-900">{value}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Empleados por departamento */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-1">Empleados por departamento</h3>
          <p className="text-sm text-gray-500 mb-4">Distribución del equipo</p>
          {!data?.by_department.length ? <EmptyState text="Sin empleados registrados" /> : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={data.by_department} layout="vertical" margin={{ top: 4, right: 24, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="departamento" tick={{ fontSize: 12 }} width={110} />
                <Tooltip content={<CustomTooltipCount />} />
                <Bar dataKey="total" name="empleados" fill="#8b5cf6" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Estado activo / inactivo — Pie + Proveedores por categoría */}
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-gray-900 mb-4">Estado de la plantilla</h3>
            {!empPieData.length ? <EmptyState text="Sin empleados aún" /> : (
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={empPieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={60}>
                    {empPieData.map((entry, i) => (
                      <Cell key={i} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-gray-900 mb-4">Proveedores por categoría</h3>
            {!data?.suppliers_by_category.length ? <EmptyState text="Sin proveedores aún" /> : (
              <div className="space-y-2">
                {data.suppliers_by_category.map((s, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                      <span className="text-sm text-gray-700">{s.categoria}</span>
                    </div>
                    <span className="text-sm font-semibold text-gray-900">{s.total}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('billing')

  return (
    <div className="p-4 md:p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Reportes</h1>
        <p className="text-gray-500 mt-1">Análisis y métricas del negocio</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg mb-8 w-fit">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-white text-indigo-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Contenido */}
      {activeTab === 'billing'   && <BillingTab />}
      {activeTab === 'inventory' && <InventoryTab />}
      {activeTab === 'hr'        && <HRTab />}
    </div>
  )
}
