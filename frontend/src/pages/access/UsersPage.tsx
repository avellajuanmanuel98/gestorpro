import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Copy, Link2, UserPlus, Users } from 'lucide-react'
import { accessApi } from '@/api/access'
import { tenantApi } from '@/api/auth'
import Badge from '@/components/ui/Badge'
import Button from '@/components/ui/Button'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import EmptyState from '@/components/ui/EmptyState'
import Input from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import PageHeader from '@/components/ui/PageHeader'
import Pagination from '@/components/ui/Pagination'
import Select from '@/components/ui/Select'
import { SkeletonTable } from '@/components/ui/Skeleton'
import { formatDate, formatDateTime } from '@/lib/dates'
import { getErrorMessage } from '@/lib/errors'
import { useAuthStore, useCan } from '@/store/authStore'
import type { Invitation, Member, Role } from '@/types'

const STATUS: Record<Member['status'], { label: string; variant: 'success' | 'warning' | 'default' }> = {
  active:    { label: 'Activo',     variant: 'success' },
  invited:   { label: 'Invitado',   variant: 'default' },
  suspended: { label: 'Suspendido', variant: 'warning' },
}

// ── Invitar ───────────────────────────────────────────────────────────────────

function InviteModal({ roles, isOpen, onClose }: { roles: Role[]; isOpen: boolean; onClose: () => void }) {
  const queryClient = useQueryClient()
  const isOwner = useAuthStore((s) => s.session?.role?.code === 'OWNER')
  const assignable = roles.filter((r) => !r.grants_all || isOwner)
  const [email, setEmail] = useState('')
  const [roleId, setRoleId] = useState<number | ''>('')
  const [created, setCreated] = useState<Invitation | null>(null)
  const [copied, setCopied] = useState(false)

  const mutation = useMutation({
    mutationFn: () => accessApi.invite({ email, role: Number(roleId) }),
    onSuccess: (invitation) => {
      setCreated(invitation)
      queryClient.invalidateQueries({ queryKey: ['invitations'] })
      queryClient.invalidateQueries({ queryKey: ['tenant-plan'] })
    },
  })

  const close = () => {
    setEmail(''); setRoleId(''); setCreated(null); setCopied(false); mutation.reset(); onClose()
  }

  const copy = async () => {
    if (!created?.invite_url) return
    await navigator.clipboard.writeText(created.invite_url)
    setCopied(true)
  }

  return (
    <Modal title={created ? 'Invitación creada' : 'Invitar usuario'} isOpen={isOpen} onClose={close} size="md"
           subtitle={created ? undefined : 'La persona recibirá acceso a esta empresa con el rol que elijas.'}>
      {created ? (
        <div className="space-y-4">
          <p className="text-sm text-zinc-600 dark:text-zinc-300">
            Comparte este enlace con <strong className="text-zinc-900 dark:text-zinc-100">{created.email}</strong> por
            el medio que prefieras. Vence el {formatDate(created.expires_at)}.
          </p>
          <div className="flex gap-2">
            <Input readOnly value={created.invite_url} leftIcon={<Link2 size={14} />} aria-label="Enlace de invitación"
                   onFocus={(e) => e.currentTarget.select()} />
            <Button variant="secondary" onClick={() => void copy()} icon={copied ? <Check size={14} /> : <Copy size={14} />}>
              {copied ? 'Copiado' : 'Copiar'}
            </Button>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            Por seguridad, este enlace solo se muestra ahora. Si lo pierdes, revoca la invitación y crea otra.
          </p>
          <div className="flex justify-end"><Button onClick={close}>Listo</Button></div>
        </div>
      ) : (
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); mutation.mutate() }}>
          <Input label="Email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                 placeholder="persona@correo.com" autoFocus />
          <Select label="Rol" id="invite-role" required value={roleId}
                  onChange={(e) => setRoleId(e.target.value ? Number(e.target.value) : '')}>
            <option value="">Selecciona un rol…</option>
            {assignable.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </Select>
          {mutation.isError && (
            <p role="alert" className="text-sm text-red-700 bg-red-50 dark:bg-red-950/40 dark:text-red-300 px-3 py-2 rounded-lg">
              {getErrorMessage(mutation.error)}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" type="button" onClick={close}>Cancelar</Button>
            <Button type="submit" loading={mutation.isPending} disabled={!email || !roleId}>Crear invitación</Button>
          </div>
        </form>
      )}
    </Modal>
  )
}

// ── Página ────────────────────────────────────────────────────────────────────

export default function UsersPage() {
  const queryClient = useQueryClient()
  const can = useCan()
  const canManage = can('access.manage_users')
  const me = useAuthStore((s) => s.session)
  const amOwner = me?.role?.code === 'OWNER'
  const [page, setPage] = useState(1)
  const [inviteOpen, setInviteOpen] = useState(false)
  const [pending, setPending] = useState<{ kind: 'remove' | 'revoke'; member?: Member; invitation?: Invitation } | null>(null)

  const members = useQuery({ queryKey: ['members', page], queryFn: () => accessApi.members({ page }),
                             placeholderData: (prev) => prev })
  const invitations = useQuery({ queryKey: ['invitations'], queryFn: accessApi.invitations })
  const roles = useQuery({ queryKey: ['roles'], queryFn: accessApi.roles })
  const plan = useQuery({ queryKey: ['tenant-plan'], queryFn: tenantApi.plan })
  const seats = plan.data?.limits.find((l) => l.key === 'users')

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['members'] })
    queryClient.invalidateQueries({ queryKey: ['invitations'] })
    queryClient.invalidateQueries({ queryKey: ['tenant-plan'] })
  }

  const update = useMutation({
    mutationFn: (args: { id: number; role?: number; status?: 'active' | 'suspended' }) =>
      accessApi.updateMember(args.id, { role: args.role, status: args.status }),
    onSuccess: refresh,
  })
  const remove = useMutation({
    mutationFn: async () => {
      if (pending?.kind === 'remove' && pending.member) await accessApi.removeMember(pending.member.id)
      if (pending?.kind === 'revoke' && pending.invitation) await accessApi.revokeInvitation(pending.invitation.id)
    },
    onSuccess: () => { refresh(); setPending(null) },
  })

  const canEdit = (m: Member) => canManage && m.email !== me?.user.email && (!m.is_owner || amOwner)
  const assignableRoles = (roles.data ?? []).filter((r) => !r.grants_all || amOwner)

  return (
    <div className="p-5 md:p-8 space-y-6 max-w-6xl mx-auto">
      <PageHeader
        title="Usuarios"
        description={seats ? `${seats.used} de ${seats.limit ?? '∞'} usuarios de tu plan` : 'Personas con acceso a la empresa'}
        actions={canManage && (
          <Button icon={<UserPlus size={15} />} onClick={() => setInviteOpen(true)}>Invitar usuario</Button>
        )}
      />

      {update.isError && (
        <p role="alert" className="text-sm text-red-700 bg-red-50 dark:bg-red-950/40 dark:text-red-300 px-4 py-2.5 rounded-lg">
          {getErrorMessage(update.error)}
        </p>
      )}

      <section className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden">
        {members.isLoading ? <SkeletonTable rows={4} /> : !members.data?.results.length ? (
          <EmptyState icon={<Users size={24} />} title="Sin usuarios" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-zinc-50/80 dark:bg-zinc-800/40 border-b border-zinc-100 dark:border-zinc-800">
                <tr className="text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                  <th className="px-6 py-3">Usuario</th>
                  <th className="px-6 py-3">Rol</th>
                  <th className="px-6 py-3">Estado</th>
                  <th className="px-6 py-3">Último acceso</th>
                  <th className="px-6 py-3 sr-only">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                {members.data.results.map((m) => (
                  <tr key={m.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/40">
                    <td className="px-6 py-3.5">
                      <p className="font-medium text-zinc-900 dark:text-zinc-100">
                        {m.full_name || m.email}{m.email === me?.user.email && <span className="text-zinc-400"> (tú)</span>}
                      </p>
                      <p className="text-xs text-zinc-500 dark:text-zinc-400">{m.email}</p>
                    </td>
                    <td className="px-6 py-3.5">
                      {canEdit(m) ? (
                        <select
                          aria-label={`Rol de ${m.email}`}
                          value={m.role.id}
                          disabled={update.isPending}
                          onChange={(e) => update.mutate({ id: m.id, role: Number(e.target.value) })}
                          className="h-8 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 px-2 text-sm text-zinc-800 dark:text-zinc-100"
                        >
                          {assignableRoles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                        </select>
                      ) : <span className="text-zinc-700 dark:text-zinc-300">{m.role.name}</span>}
                    </td>
                    <td className="px-6 py-3.5"><Badge variant={STATUS[m.status].variant} dot>{STATUS[m.status].label}</Badge></td>
                    <td className="px-6 py-3.5 text-zinc-600 dark:text-zinc-400 tabular-nums">{formatDateTime(m.last_login)}</td>
                    <td className="px-6 py-3.5 text-right whitespace-nowrap">
                      {canEdit(m) && (
                        <div className="flex justify-end gap-1">
                          <Button size="xs" variant="ghost" loading={update.isPending && update.variables?.id === m.id && !!update.variables?.status}
                                  onClick={() => update.mutate({ id: m.id, status: m.status === 'active' ? 'suspended' : 'active' })}>
                            {m.status === 'active' ? 'Suspender' : 'Reactivar'}
                          </Button>
                          <Button size="xs" variant="ghost" className="text-red-600 dark:text-red-400"
                                  onClick={() => setPending({ kind: 'remove', member: m })}>
                            Quitar
                          </Button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <Pagination data={members.data} onPageChange={setPage} noun="usuarios" isFetching={members.isFetching} />
      </section>

      {(invitations.data?.length ?? 0) > 0 && (
        <section className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden">
          <h2 className="px-6 py-4 text-sm font-semibold text-zinc-900 dark:text-zinc-100 border-b border-zinc-100 dark:border-zinc-800">
            Invitaciones pendientes
          </h2>
          <ul className="divide-y divide-zinc-100 dark:divide-zinc-800">
            {invitations.data!.map((inv) => (
              <li key={inv.id} className="flex items-center justify-between gap-4 px-6 py-3 text-sm">
                <div>
                  <p className="font-medium text-zinc-900 dark:text-zinc-100">{inv.email}</p>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">{inv.role.name} · vence el {formatDate(inv.expires_at)}</p>
                </div>
                {canManage && (
                  <Button size="xs" variant="ghost" onClick={() => setPending({ kind: 'revoke', invitation: inv })}>Revocar</Button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <InviteModal roles={roles.data ?? []} isOpen={inviteOpen} onClose={() => setInviteOpen(false)} />

      <ConfirmDialog
        isOpen={pending !== null}
        title={pending?.kind === 'revoke' ? 'Revocar invitación' : 'Quitar acceso'}
        description={pending?.kind === 'revoke'
          ? <>El enlace enviado a <strong>{pending.invitation?.email}</strong> dejará de funcionar.</>
          : <><strong>{pending?.member?.email}</strong> perderá el acceso a esta empresa de inmediato. Su cuenta y sus
              registros en la auditoría se conservan.</>}
        confirmLabel={pending?.kind === 'revoke' ? 'Revocar' : 'Quitar acceso'}
        loading={remove.isPending}
        error={remove.isError ? getErrorMessage(remove.error) : null}
        onConfirm={() => remove.mutate()}
        onClose={() => { setPending(null); remove.reset() }}
      />
    </div>
  )
}
