import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, Plus, AlertTriangle, Pencil, Trash2, Package, Tag } from 'lucide-react'
import { inventoryApi } from '@/api/inventory'
import type { Product, Category } from '@/types'
import Modal from '@/components/ui/Modal'
import ProductForm from '@/components/inventory/ProductForm'

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatCurrency(v: string | number) {
  return new Intl.NumberFormat('es-CO', {
    style: 'currency', currency: 'COP', minimumFractionDigits: 0,
  }).format(Number(v))
}

// ── Tab: Productos ────────────────────────────────────────────────────────────

function ProductsTab() {
  const queryClient = useQueryClient()
  const [search,     setSearch]     = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [modalOpen,  setModalOpen]  = useState(false)
  const [selected,   setSelected]   = useState<Product | undefined>()

  const { data, isLoading } = useQuery({
    queryKey: ['products', search, typeFilter],
    queryFn:  () => inventoryApi.listProducts({
      search,
      ...(typeFilter ? { product_type: typeFilter } : {}),
    }),
    enabled: search.length !== 1,
  })

  const deleteMutation = useMutation({
    mutationFn: inventoryApi.deleteProduct,
    onSuccess:  () => queryClient.invalidateQueries({ queryKey: ['products'] }),
  })

  const openCreate = () => { setSelected(undefined); setModalOpen(true) }
  const openEdit   = (p: Product) => { setSelected(p); setModalOpen(true) }

  const handleDelete = (p: Product) => {
    if (confirm(`¿Eliminar "${p.name}"? Esta acción no se puede deshacer.`)) {
      deleteMutation.mutate(p.id)
    }
  }

  return (
    <>
      {/* Controles */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar por nombre o código..."
            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <select
          value={typeFilter}
          onChange={e => setTypeFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="">Todos los tipos</option>
          <option value="product">Productos</option>
          <option value="service">Servicios</option>
        </select>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors shrink-0"
        >
          <Plus size={16} />Nuevo producto
        </button>
      </div>

      {/* Tabla */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden overflow-x-auto">
          {!data?.results.length ? (
            <div className="text-center py-12 text-gray-500">No se encontraron productos</div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Producto</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Categoría</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Precio</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Stock</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Estado</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.results.map(product => (
                  <tr key={product.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center shrink-0">
                          <Package size={14} className="text-indigo-400" />
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{product.name}</p>
                          <p className="text-xs text-gray-400">{product.code}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {product.category_name ? (
                        <span className="inline-flex items-center gap-1 text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                          <Tag size={11} />{product.category_name}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700 font-medium">
                      {formatCurrency(product.price)}
                    </td>
                    <td className="px-6 py-4">
                      {product.product_type === 'service' ? (
                        <span className="text-xs text-gray-400">Servicio</span>
                      ) : (
                        <div className="flex items-center gap-1.5">
                          {product.is_low_stock && (
                            <AlertTriangle size={13} className="text-amber-500 shrink-0" />
                          )}
                          <span className={`text-sm font-medium ${
                            product.stock === 0        ? 'text-red-600'
                            : product.is_low_stock     ? 'text-amber-600'
                            : 'text-gray-700'
                          }`}>
                            {product.stock} uds
                          </span>
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        product.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {product.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => openEdit(product)}
                          className="p-1.5 rounded-lg hover:bg-indigo-50 text-gray-500 hover:text-indigo-600 transition-colors"
                          title="Editar"
                        >
                          <Pencil size={15} />
                        </button>
                        <button
                          onClick={() => handleDelete(product)}
                          className="p-1.5 rounded-lg hover:bg-red-50 text-gray-500 hover:text-red-600 transition-colors"
                          title="Eliminar"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      <Modal
        title={selected ? 'Editar producto' : 'Nuevo producto'}
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        size="lg"
      >
        <ProductForm product={selected} onSuccess={() => setModalOpen(false)} />
      </Modal>
    </>
  )
}

// ── Tab: Categorías ───────────────────────────────────────────────────────────

function CategoriesTab() {
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen]   = useState(false)
  const [selected,  setSelected]    = useState<Category | undefined>()
  const [name,      setName]        = useState('')
  const [desc,      setDesc]        = useState('')
  const [saving,    setSaving]      = useState(false)
  const [error,     setError]       = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['categories'],
    queryFn:  inventoryApi.listCategories,
  })

  const deleteMutation = useMutation({
    mutationFn: inventoryApi.deleteCategory,
    onSuccess:  () => queryClient.invalidateQueries({ queryKey: ['categories'] }),
  })

  const openCreate = () => {
    setSelected(undefined); setName(''); setDesc(''); setError(''); setModalOpen(true)
  }
  const openEdit = (c: Category) => {
    setSelected(c); setName(c.name); setDesc(c.description); setError(''); setModalOpen(true)
  }

  const handleSave = async () => {
    if (!name.trim()) { setError('El nombre es requerido'); return }
    setSaving(true)
    try {
      if (selected) {
        await inventoryApi.updateCategory(selected.id, { name, description: desc })
      } else {
        await inventoryApi.createCategory({ name, description: desc })
      }
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      setModalOpen(false)
    } catch {
      setError('Error al guardar. ¿El nombre ya existe?')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = (c: Category) => {
    if (confirm(`¿Eliminar la categoría "${c.name}"? Los productos quedarán sin categoría.`)) {
      deleteMutation.mutate(c.id)
    }
  }

  return (
    <>
      <div className="flex justify-end mb-6">
        <button
          onClick={openCreate}
          className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          <Plus size={16} />Nueva categoría
        </button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {!data?.results.length ? (
            <div className="text-center py-12 text-gray-500">No hay categorías aún</div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Categoría</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Descripción</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Productos</th>
                  <th className="text-left text-xs font-medium text-gray-500 uppercase px-6 py-3">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.results.map(cat => (
                  <tr key={cat.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 font-medium text-gray-900">{cat.name}</td>
                    <td className="px-6 py-4 text-sm text-gray-500">{cat.description || '—'}</td>
                    <td className="px-6 py-4 text-sm text-gray-700">{cat.products_count}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <button onClick={() => openEdit(cat)} className="p-1.5 rounded-lg hover:bg-indigo-50 text-gray-500 hover:text-indigo-600 transition-colors" title="Editar">
                          <Pencil size={15} />
                        </button>
                        <button onClick={() => handleDelete(cat)} className="p-1.5 rounded-lg hover:bg-red-50 text-gray-500 hover:text-red-600 transition-colors" title="Eliminar">
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Modal categoría (simple, sin react-hook-form) */}
      <Modal
        title={selected ? 'Editar categoría' : 'Nueva categoría'}
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Electrónica, Ropa, Servicios..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Descripción (opcional)</label>
            <textarea
              value={desc}
              onChange={e => setDesc(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            />
          </div>
          {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}
          <div className="flex justify-end">
            <button
              onClick={handleSave}
              disabled={saving}
              className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors disabled:opacity-50"
            >
              {saving ? 'Guardando...' : selected ? 'Guardar cambios' : 'Crear categoría'}
            </button>
          </div>
        </div>
      </Modal>
    </>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────

type TabId = 'products' | 'categories'

export default function InventoryPage() {
  const [activeTab, setActiveTab] = useState<TabId>('products')

  const { data: products } = useQuery({
    queryKey: ['products'],
    queryFn:  () => inventoryApi.listProducts({}),
  })
  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn:  inventoryApi.listCategories,
  })

  return (
    <div className="p-4 md:p-8">
      {/* Encabezado */}
      <div className="flex items-center justify-between mb-6 md:mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Inventario</h1>
          <p className="text-gray-500 mt-1">
            {products?.count ?? 0} productos · {categories?.count ?? 0} categorías
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg mb-6 w-fit">
        {([
          { id: 'products',   label: 'Productos'   },
          { id: 'categories', label: 'Categorías'  },
        ] as { id: TabId; label: string }[]).map(tab => (
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

      {activeTab === 'products'   && <ProductsTab />}
      {activeTab === 'categories' && <CategoriesTab />}
    </div>
  )
}
