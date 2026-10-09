import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Lock, Plus, ShieldCheck } from 'lucide-react'
import { accessApi } from '@/api/access'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import Input from '@/components/ui/Input'
import PageHeader from '@/components/ui/PageHeader'
import { SkeletonTable } from '@/components/ui/Skeleton'
import { getErrorMessage } from '@/lib/errors'
import { useAuthStore, useCan, useHasFeature } from '@/store/authStore'
import type { PermissionDef, Role } from '@/types'

const MODULE_LABELS: Record<string, string> = {
  tenancy: 'Empresa', access: 'Usuarios y roles', audit: 'Auditoría', customers: 'Clientes',
  suppliers: 'Proveedores', catalog: 'Catálogo', billing: 'Facturación', reporting: 'Reportes',
  hr: 'Personal', assistant: 'Asistente IA',
}

function groupByModule(perms: PermissionDef[]) {
  const groups = new Map<string, PermissionDef[]>()
  for (const p of perms) groups.set(p.module, [...(groups.get(p.module) ?? []), p])
  return [...groups.entries()]
}

function RoleEditor({ role, catalog, onDone }: { role: Role | null; catalog: PermissionDef[]; onDone: () => void }) {
  const queryClient = useQueryClient()
  const myPermissions = useAuthStore((s) => s.session?.permissions ?? [])
  const isOwner = useAuthStore((s) => s.session?.role?.code === 'OWNER')
  const canManage = useCan()('access.manage_roles')
  const readOnly = !canManage || role?.grants_all === true
  const [name, setName] = useState(role?.name ?? '')
  const [selected, setSelected] = useState<Set<string>>(new Set(role?.permissions.filter((p) => p !== '*') ?? []))
  const [confirmDelete, setConfirmDelete] = useState(false)

  const save = useMutation({
    mutationFn: () => {
      const permissions = [...selected]
      if (!role) return accessApi.createRole({ name, permissions })
      return accessApi.updateRole(role.id, { ...(role.is_system ? {} : { name }), permissions })
    },
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['roles'] }); if (!role) onDone() },
  })
  const remove = useMutation({
    mutationFn: () => accessApi.deleteRole(role!.id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['roles'] }); onDone() },
  })

  const toggle = (code: string) => setSelected((prev) => {
    const next = new Set(prev)
    if (next.has(code)) next.delete(code)
    else next.add(code)
    return next
  })

  // Anti-escalada (el backend lo exige): solo puedes otorgar permisos que tienes.
  const canGrant = (code: string) => isOwner || myPermissions.includes(code)

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        {role?.is_system || readOnly ? (
          <div>
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100">{role?.name}</h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
              {role?.grants_all ? 'Tiene todos los permisos, incluidos los de módulos futuros. No se puede modificar.'
                : 'Rol del sistema: puedes ajustar sus permisos, no su nombre.'}
            </p>
          </div>
        ) : (
          <div className="w-full max-w-sm">
            <Input label="Nombre del rol" value={name} onChange={(e) => setName(e.target.value)} placeholder="Ej.: Hornero" />
          </div>
        )}
        {role && !role.is_system && canManage && (
          <Button variant="ghost" size="sm" className="text-red-600 dark:text-red-400" onClick={() => setConfirmDelete(true)}>
            Eliminar rol
          </Button>
        )}
      </div>

      {role?.grants_all ? null : (
        <div className="grid gap-4 md:grid-cols-2">
          {groupByModule(catalog).map(([module, perms]) => (
            <fieldset key={module} className="rounded-xl border border-zinc-200 dark:border-zinc-800 p-4">
              <legend className="px-1 text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                {MODULE_LABELS[module] ?? module}
                {!perms[0].available && <span className="ml-2 normal-case tracking-normal font-normal">· no incluido en tu plan</span>}
              </legend>
              <div className="space-y-2 mt-1">
                {perms.map((p) => {
                  const disabled = readOnly || !p.available || (!canGrant(p.code) && !selected.has(p.code))
                  return (
                    <label key={p.code} className={`flex items-start gap-2.5 text-sm ${disabled ? 'opacity-50' : 'cursor-pointer'}`}>
                      <input type="checkbox" className="mt-0.5 accent-indigo-600" checked={selected.has(p.code)}
                             disabled={disabled} onChange={() => toggle(p.code)} />
                      <span className="text-zinc-700 dark:text-zinc-300">
                        {p.description}
                        {!canGrant(p.code) && p.available && !readOnly && (
                          <span className="block text-[11px] text-zinc-400">Tú no tienes este permiso</span>
                        )}
                      </span>
                    </label>
                  )
                })}
              </div>
            </fieldset>
          ))}
        </div>
      )}

      {save.isError && (
        <p role="alert" className="text-sm text-red-700 bg-red-50 dark:bg-red-950/40 dark:text-red-300 px-3 py-2 rounded-lg">
          {getErrorMessage(save.error)}
        </p>
      )}
      {save.isSuccess && role && <p className="text-sm text-emerald-700 dark:text-emerald-400">Cambios guardados.</p>}

      {!readOnly && (
        <div className="flex justify-end gap-2">
          {!role && <Button variant="ghost" onClick={onDone}>Cancelar</Button>}
          <Button onClick={() => save.mutate()} loading={save.isPending} disabled={!role && !name.trim()}>
            {role ? 'Guardar permisos' : 'Crear rol'}
          </Button>
        </div>
      )}

      <ConfirmDialog
        isOpen={confirmDelete}
        title="Eliminar rol"
        description={<>Se eliminará el rol <strong>{role?.name}</strong>. Solo es posible si nadie lo tiene asignado.</>}
        confirmLabel="Eliminar"
        loading={remove.isPending}
        error={remove.isError ? getErrorMessage(remove.error) : null}
        onConfirm={() => remove.mutate()}
        onClose={() => { setConfirmDelete(false); remove.reset() }}
      />
    </div>
  )
}

export default function RolesPage() {
  const canManage = useCan()('access.manage_roles')
  const hasCustomRoles = useHasFeature()('custom_roles')
  const roles = useQuery({ queryKey: ['roles'], queryFn: accessApi.roles })
  const catalog = useQuery({ queryKey: ['permission-catalog'], queryFn: accessApi.permissions })
  const [selectedId, setSelectedId] = useState<number | 'new' | null>(null)

  const selected = useMemo(() => {
    if (selectedId === 'new') return null
    return roles.data?.find((r) => r.id === selectedId) ?? roles.data?.[0] ?? null
  }, [roles.data, selectedId])

  return (
    <div className="p-5 md:p-8 space-y-6 max-w-6xl mx-auto">
      <PageHeader
        title="Roles y permisos"
        description="Qué puede hacer cada persona. El sistema valida cada permiso en el servidor."
        actions={canManage && (hasCustomRoles
          ? <Button icon={<Plus size={15} />} onClick={() => setSelectedId('new')}>Nuevo rol</Button>
          : <span className="text-xs text-zinc-500 dark:text-zinc-400 flex items-center gap-1.5"><Lock size={13} />
              Los roles personalizados están disponibles en planes superiores</span>)}
      />

      {roles.isLoading || catalog.isLoading ? <SkeletonTable rows={5} /> : (
        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          <nav aria-label="Roles" className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-2 h-fit">
            {roles.data?.map((r) => {
              const active = selectedId !== 'new' && selected?.id === r.id
              return (
                <button key={r.id} onClick={() => setSelectedId(r.id)}
                        className={`w-full flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-sm text-left transition-colors ${
                          active ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300'
                                 : 'text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800'}`}>
                  <span className="flex items-center gap-2 truncate">
                    {r.grants_all && <ShieldCheck size={14} className="shrink-0" />}{r.name}
                  </span>
                  <span className="flex items-center gap-1.5 shrink-0">
                    {!r.is_system && <Badge size="sm">Personalizado</Badge>}
                    <span className="text-xs text-zinc-400 tabular-nums" title="Usuarios activos">{r.members_count}</span>
                  </span>
                </button>
              )
            })}
          </nav>
          <section className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6">
            <RoleEditor key={selectedId === 'new' ? 'new' : selected?.id} role={selectedId === 'new' ? null : selected}
                        catalog={catalog.data ?? []} onDone={() => setSelectedId(null)} />
          </section>
        </div>
      )}
    </div>
  )
}
