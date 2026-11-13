import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CreditCard, Plus, Wallet } from 'lucide-react'
import { PAYMENT_KINDS, posConfigApi, type PaymentKind, type PaymentMethodConfig, type RegisterConfig } from '@/api/posConfig'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import { Card, CardHeader } from '@/components/ui/Card'
import Input from '@/components/ui/Input'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import Select from '@/components/ui/Select'
import { SkeletonText } from '@/components/ui/Skeleton'
import Switch from '@/components/ui/Switch'
import { cn } from '@/lib/cn'
import { getErrorMessage } from '@/lib/errors'
import { toast } from '@/store/toastStore'

/** Nombre editable en el sitio: se guarda al salir del campo o con Enter. */
function InlineName({ value, onSave, label }: { value: string; onSave: (v: string) => void; label: string }) {
  const [draft, setDraft] = useState(value)
  const commit = () => { const v = draft.trim(); if (v && v !== value) onSave(v); else setDraft(value) }
  return (
    <input aria-label={label} value={draft} onChange={(e) => setDraft(e.target.value)} onBlur={commit}
           onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); if (e.key === 'Escape') setDraft(value) }}
           className="w-full min-w-0 h-8 rounded-lg border border-transparent hover:border-line-strong focus:border-line-strong bg-transparent px-2 -mx-2 text-sm font-medium text-ink" />
  )
}

function RegistersCard() {
  const queryClient = useQueryClient()
  const registers = useQuery({ queryKey: ['config', 'registers'], queryFn: posConfigApi.registers })
  const locations = useQuery({ queryKey: ['config', 'locations'], queryFn: posConfigApi.locations })
  const [name, setName] = useState('')
  const [location, setLocation] = useState('')
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['config', 'registers'] })
    void queryClient.invalidateQueries({ queryKey: ['cash-registers'] })
  }
  const create = useMutation({
    mutationFn: () => posConfigApi.createRegister({ name, ...(location && { location: Number(location) }) }),
    onSuccess: (r) => { refresh(); setName(''); toast.success(`Caja "${r.name}" creada`) },
  })
  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Parameters<typeof posConfigApi.updateRegister>[1] }) => posConfigApi.updateRegister(id, body),
    onSuccess: refresh,
    onError: (e) => toast.error(getErrorMessage(e)),
  })
  const multi = (locations.data?.length ?? 0) > 1
  return (
    <Card>
      <CardHeader title="Cajas" description="Cada caja tiene su propio turno: abre una por cada cajón de dinero que manejen." />
      {registers.isLoading ? <div className="px-5 pb-5"><SkeletonText lines={3} /></div> : (
        <ul className="divide-y divide-line border-t border-line">
          {registers.data?.map((r: RegisterConfig) => (
            <li key={r.id} className={cn('flex items-center gap-3 px-5 py-2.5', !r.is_active && 'opacity-60')}>
              <Wallet size={16} className="text-ink-subtle shrink-0" aria-hidden />
              <div className="flex-1 min-w-0">
                <InlineName value={r.name} label={`Nombre de ${r.name}`} onSave={(v) => update.mutate({ id: r.id, body: { name: v } })} />
                <p className="text-xs text-ink-muted">{multi && `${r.location_name} · `}{r.open_session_by ? `Turno abierto por ${r.open_session_by}` : r.is_active ? 'Sin turno abierto' : 'Desactivada'}</p>
              </div>
              <Switch checked={r.is_active} label={`${r.name} activa`} disabled={update.isPending}
                      onChange={(v) => update.mutate({ id: r.id, body: { is_active: v } })} />
            </li>
          ))}
        </ul>
      )}
      <form className="flex flex-wrap items-end gap-2 px-5 py-4 border-t border-line" onSubmit={(e) => { e.preventDefault(); create.mutate() }}>
        <div className="flex-1 min-w-48"><Input label="Nueva caja" placeholder="Ej.: Caja 2, Mostrador" value={name} onChange={(e) => setName(e.target.value)} /></div>
        {multi && (
          <div className="w-48"><Select label="Sucursal" value={location} onChange={(e) => setLocation(e.target.value)}>
            <option value="">Principal</option>
            {locations.data?.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
          </Select></div>
        )}
        <Button type="submit" variant="outline" icon={<Plus size={14} />} loading={create.isPending} disabled={!name.trim()}>Agregar</Button>
      </form>
      {create.isError && <div className="px-5 pb-4"><Alert tone="danger">{getErrorMessage(create.error)}</Alert></div>}
    </Card>
  )
}

function MethodsCard() {
  const queryClient = useQueryClient()
  const methods = useQuery({ queryKey: ['config', 'methods'], queryFn: posConfigApi.methods })
  const [name, setName] = useState('')
  const [kind, setKind] = useState<PaymentKind>('card')
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['config', 'methods'] })
    void queryClient.invalidateQueries({ queryKey: ['payment-methods'] })
  }
  const create = useMutation({
    mutationFn: () => posConfigApi.createMethod({ name, kind }),
    onSuccess: (m) => { refresh(); setName(''); toast.success(`"${m.name}" agregado`) },
  })
  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Parameters<typeof posConfigApi.updateMethod>[1] }) => posConfigApi.updateMethod(id, body),
    onSuccess: refresh,
    onError: (e) => toast.error(getErrorMessage(e)),
  })
  return (
    <Card>
      <CardHeader title="Medios de pago" description="Lo que aparece al cobrar. Solo el efectivo da cambio y entra al cajón; los demás se concilian aparte." />
      {methods.isLoading ? <div className="px-5 pb-5"><SkeletonText lines={4} /></div> : (
        <ul className="divide-y divide-line border-t border-line">
          {methods.data?.map((m: PaymentMethodConfig) => (
            <li key={m.id} className={cn('flex items-center gap-3 px-5 py-2.5', !m.is_active && 'opacity-60')}>
              <CreditCard size={16} className="text-ink-subtle shrink-0" aria-hidden />
              <div className="flex-1 min-w-0">
                <InlineName value={m.name} label={`Nombre de ${m.name}`} onSave={(v) => update.mutate({ id: m.id, body: { name: v } })} />
              </div>
              <select aria-label={`Tipo de ${m.name}`} value={m.kind} disabled={m.code === 'cash' || update.isPending}
                      onChange={(e) => update.mutate({ id: m.id, body: { kind: e.target.value as PaymentKind } })}
                      className="h-8 rounded-lg border border-line-strong bg-surface px-2 text-sm text-ink disabled:opacity-60">
                {PAYMENT_KINDS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
              </select>
              <Switch checked={m.is_active} label={`${m.name} activo`} disabled={update.isPending}
                      onChange={(v) => update.mutate({ id: m.id, body: { is_active: v } })} />
            </li>
          ))}
        </ul>
      )}
      <form className="flex flex-wrap items-end gap-2 px-5 py-4 border-t border-line" onSubmit={(e) => { e.preventDefault(); create.mutate() }}>
        <div className="flex-1 min-w-48"><Input label="Nuevo medio de pago" placeholder="Ej.: Bold, Bancolombia QR" value={name} onChange={(e) => setName(e.target.value)} /></div>
        <div className="w-48"><Select label="Tipo" value={kind} onChange={(e) => setKind(e.target.value as PaymentKind)}>
          {PAYMENT_KINDS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </Select></div>
        <Button type="submit" variant="outline" icon={<Plus size={14} />} loading={create.isPending} disabled={!name.trim()}>Agregar</Button>
      </form>
      {create.isError && <div className="px-5 pb-4"><Alert tone="danger">{getErrorMessage(create.error)}</Alert></div>}
    </Card>
  )
}

export default function PosSettingsPage() {
  return (
    <Page width="narrow">
      <PageHeader title="Caja y pagos" description="Cajas y medios de pago que usa el punto de venta. Los cambios quedan en la auditoría." />
      <RegistersCard />
      <MethodsCard />
    </Page>
  )
}
