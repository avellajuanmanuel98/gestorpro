import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Search, Plus, Mail, Phone, MapPin,
  Pencil, Trash2, Users, MoreHorizontal,
} from 'lucide-react'
import { clientsApi } from '@/api/clients'
import type { Client } from '@/types'
import Modal from '@/components/ui/Modal'
import ClientForm from '@/components/clients/ClientForm'
import Button from '@/components/ui/Button'
import Badge from '@/components/ui/Badge'
import EmptyState from '@/components/ui/EmptyState'
import { SkeletonTable } from '@/components/ui/Skeleton'

// ── Avatar ────────────────────────────────────────────────────────────────────

const AVATAR_COLORS = [
  'from-indigo-500 to-violet-600',
  'from-emerald-500 to-teal-600',
  'from-amber-500  to-orange-600',
  'from-rose-500   to-pink-600',
  'from-cyan-500   to-blue-600',
  'from-violet-500 to-purple-600',
]

function ClientAvatar({ name }: { name: string }) {
  const initials = name
    .split(' ')
    .slice(0, 2)
    .map((n) => n[0])
    .join('')
    .toUpperCase()

  const colorIndex =
    name.charCodeAt(0) % AVATAR_COLORS.length

  return (
    <div
      className={[
        'w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-white shrink-0',
        'bg-gradient-to-br',
        AVATAR_COLORS[colorIndex],
        'ring-2 ring-white dark:ring-zinc-900',
      ].join(' ')}
    >
      {initials}
    </div>
  )
}

// ── Row actions (dropdown stub) ───────────────────────────────────────────────

function RowActions({
  client,
  onEdit,
  onDelete,
}: {
  client:   Client
  onEdit:   (c: Client) => void
  onDelete: (c: Client) => void
}) {
  return (
    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      <button
        onClick={() => onEdit(client)}
        title="Editar"
        className="p-1.5 rounded-lg text-zinc-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:text-indigo-400 dark:hover:bg-indigo-950/40 transition-colors"
      >
        <Pencil size={14} />
      </button>
      <button
        onClick={() => onDelete(client)}
        title="Eliminar"
        className="p-1.5 rounded-lg text-zinc-400 hover:text-red-600 hover:bg-red-50 dark:hover:text-red-400 dark:hover:bg-red-950/40 transition-colors"
      >
        <Trash2 size={14} />
      </button>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ClientsPage() {
  const queryClient = useQueryClient()
  const [search,         setSearch]         = useState('')
  const [modalOpen,      setModalOpen]      = useState(false)
  const [selectedClient, setSelectedClient] = useState<Client | undefined>()

  const { data, isLoading } = useQuery({
    queryKey: ['clients', search],
    queryFn:  () => clientsApi.list({ search }),
    enabled:  search.length !== 1,
  })

  const deleteMutation = useMutation({
    mutationFn: clientsApi.delete,
    onSuccess:  () => queryClient.invalidateQueries({ queryKey: ['clients'] }),
  })

  const openCreate = () => {
    setSelectedClient(undefined)
    setModalOpen(true)
  }

  const openEdit = (client: Client) => {
    setSelectedClient(client)
    setModalOpen(true)
  }

  const handleDelete = (client: Client) => {
    if (confirm(`¿Eliminar a ${client.full_name}? Esta acción no se puede deshacer.`)) {
      deleteMutation.mutate(client.id)
    }
  }

  const totalCount = data?.count ?? 0

  return (
    <div className="p-5 md:p-8 space-y-6 max-w-7xl mx-auto">

      {/* ── Header ── */}
      <div className="animate-fade-down flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 tracking-tight">
            Clientes
          </h1>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">
            {isLoading ? 'Cargando...' : `${totalCount} cliente${totalCount !== 1 ? 's' : ''} registrado${totalCount !== 1 ? 's' : ''}`}
          </p>
        </div>

        <Button
          variant="primary"
          size="md"
          icon={<Plus size={15} />}
          onClick={openCreate}
        >
          Nuevo cliente
        </Button>
      </div>

      {/* ── Filters bar ── */}
      <div className="animate-fade-up flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 dark:text-zinc-500 pointer-events-none"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar por nombre, email o documento…"
            className={[
              'w-full h-9 pl-8 pr-3 text-sm rounded-lg',
              'bg-white dark:bg-zinc-900/60',
              'border border-zinc-200 dark:border-zinc-700',
              'text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 dark:placeholder:text-zinc-500',
              'focus:outline-none focus:ring-2 focus:ring-indigo-500/25 focus:border-indigo-400',
              'transition-all duration-150',
            ].join(' ')}
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
            >
              ×
            </button>
          )}
        </div>
      </div>

      {/* ── Table ── */}
      <div className="animate-fade-up delay-100 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden">

        {isLoading ? (
          <SkeletonTable rows={6} />
        ) : !data?.results.length ? (
          <EmptyState
            icon={<Users size={24} />}
            title={search ? 'Sin resultados' : 'Aún no hay clientes'}
            description={
              search
                ? `No se encontraron clientes con "${search}". Intenta con otro término.`
                : 'Agrega tu primer cliente para comenzar a gestionar tus ventas.'
            }
            action={
              !search
                ? { label: 'Agregar cliente', onClick: openCreate, icon: <Plus size={14} /> }
                : undefined
            }
          />
        ) : (
          <>
            {/* Table header */}
            <div className="grid grid-cols-[1fr_1fr_140px_80px_80px] items-center px-6 py-3 border-b border-zinc-100 dark:border-zinc-800 bg-zinc-50/80 dark:bg-zinc-800/40">
              {['Cliente', 'Contacto', 'Ciudad', 'Estado', ''].map((h, i) => (
                <span key={i} className="text-[11px] font-semibold uppercase tracking-wider text-zinc-400 dark:text-zinc-500">
                  {h}
                </span>
              ))}
            </div>

            {/* Rows */}
            <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
              {data.results.map((client) => (
                <div
                  key={client.id}
                  className="group grid grid-cols-[1fr_1fr_140px_80px_80px] items-center px-6 py-3.5 hover:bg-zinc-50 dark:hover:bg-zinc-800/40 transition-colors"
                >
                  {/* Client name + company */}
                  <div className="flex items-center gap-3 min-w-0">
                    <ClientAvatar name={client.full_name} />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate">
                        {client.full_name}
                      </p>
                      {client.company_name && (
                        <p className="text-xs text-zinc-400 dark:text-zinc-500 truncate">
                          {client.company_name}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Contact */}
                  <div className="min-w-0 space-y-0.5">
                    <div className="flex items-center gap-1.5 text-xs text-zinc-600 dark:text-zinc-400">
                      <Mail size={11} className="shrink-0 text-zinc-400" />
                      <span className="truncate">{client.email}</span>
                    </div>
                    {client.phone && (
                      <div className="flex items-center gap-1.5 text-xs text-zinc-500 dark:text-zinc-500">
                        <Phone size={11} className="shrink-0 text-zinc-400" />
                        <span>{client.phone}</span>
                      </div>
                    )}
                  </div>

                  {/* City */}
                  <div>
                    {client.city ? (
                      <div className="flex items-center gap-1.5 text-xs text-zinc-600 dark:text-zinc-400">
                        <MapPin size={11} className="shrink-0 text-zinc-400" />
                        <span className="truncate">{client.city}</span>
                      </div>
                    ) : (
                      <span className="text-xs text-zinc-300 dark:text-zinc-600">—</span>
                    )}
                  </div>

                  {/* Status */}
                  <div>
                    <Badge
                      variant={client.status === 'active' ? 'success' : 'default'}
                      dot
                    >
                      {client.status === 'active' ? 'Activo' : 'Inactivo'}
                    </Badge>
                  </div>

                  {/* Actions */}
                  <div className="flex justify-end">
                    <RowActions
                      client={client}
                      onEdit={openEdit}
                      onDelete={handleDelete}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Table footer */}
            <div className="px-6 py-3 border-t border-zinc-100 dark:border-zinc-800 bg-zinc-50/60 dark:bg-zinc-800/20">
              <p className="text-xs text-zinc-400 dark:text-zinc-500">
                Mostrando {data.results.length} de {totalCount} cliente{totalCount !== 1 ? 's' : ''}
              </p>
            </div>
          </>
        )}
      </div>

      {/* ── Modal ── */}
      <Modal
        title={selectedClient ? 'Editar cliente' : 'Nuevo cliente'}
        subtitle={selectedClient ? 'Actualiza la información del cliente' : 'Completa los datos del nuevo cliente'}
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        size="lg"
      >
        <ClientForm
          client={selectedClient}
          onSuccess={() => setModalOpen(false)}
        />
      </Modal>
    </div>
  )
}
