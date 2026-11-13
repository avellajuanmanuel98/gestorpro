import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Pencil } from 'lucide-react'
import { FEATURE_LABELS, LIMIT_LABELS, platformApi, type PlatformPlan } from '@/api/platform'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import Input from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import PageHeader, { Page } from '@/components/ui/PageHeader'
import { Skeleton } from '@/components/ui/Skeleton'
import { cn } from '@/lib/cn'
import { getErrorMessage } from '@/lib/errors'
import { formatCOP } from '@/lib/money'

function PlanForm({ plan, onDone }: { plan: PlatformPlan; onDone: () => void }) {
  const queryClient = useQueryClient()
  const [name, setName] = useState(plan.name)
  const [description, setDescription] = useState(plan.description)
  const [price, setPrice] = useState(plan.price_monthly ? String(Number(plan.price_monthly)) : '')
  const [isPublic, setIsPublic] = useState(plan.is_public)
  const [isActive, setIsActive] = useState(plan.is_active)
  const [features, setFeatures] = useState<string[]>(plan.features)
  const [limits, setLimits] = useState<Record<string, string>>(
    Object.fromEntries(Object.keys(LIMIT_LABELS).map((k) => [k, plan.limits[k] === null || plan.limits[k] === undefined ? (k in plan.limits ? '' : '0') : String(plan.limits[k])])))
  const save = useMutation({
    mutationFn: () => platformApi.updatePlan(plan.id, {
      name, description, price_monthly: price.trim() === '' ? null : price.replace(/\./g, '').replace(',', '.'),
      is_public: isPublic, is_active: isActive, features,
      limits: Object.fromEntries(Object.entries(limits).map(([k, v]) => [k, v.trim() === '' ? null : Number(v)])),
    }),
    onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ['platform'] }); onDone() },
  })
  return (
    <form className="space-y-5" onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
      <div className="grid sm:grid-cols-2 gap-4">
        <Input label="Nombre" required value={name} onChange={(e) => setName(e.target.value)} />
        <Input label="Precio mensual (COP)" inputMode="numeric" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="Vacío = por definir" />
      </div>
      <Input label="Descripción" value={description} onChange={(e) => setDescription(e.target.value)} />
      <fieldset>
        <legend className="text-sm font-medium text-ink mb-2">Funcionalidades</legend>
        <div className="grid sm:grid-cols-2 gap-2">
          {Object.entries(FEATURE_LABELS).map(([key, label]) => (
            <label key={key} className="flex items-center gap-2 text-sm text-ink">
              <input type="checkbox" className="accent-[var(--primary)]" checked={features.includes(key)}
                     onChange={(e) => setFeatures((f) => (e.target.checked ? [...f, key] : f.filter((x) => x !== key)))} />{label}
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend className="text-sm font-medium text-ink mb-2">Límites <span className="font-normal text-ink-muted">(vacío = ilimitado)</span></legend>
        <div className="grid grid-cols-2 gap-4">
          {Object.entries(LIMIT_LABELS).map(([key, label]) => (
            <Input key={key} label={label} inputMode="numeric" value={limits[key]} placeholder="Ilimitado"
                   onChange={(e) => setLimits((l) => ({ ...l, [key]: e.target.value.replace(/\D/g, '') }))} />
          ))}
        </div>
      </fieldset>
      <div className="flex flex-wrap gap-6 text-sm text-ink">
        <label className="flex items-center gap-2"><input type="checkbox" className="accent-[var(--primary)]" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} />Visible en la página de precios</label>
        <label className="flex items-center gap-2"><input type="checkbox" className="accent-[var(--primary)]" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />Activo (se puede asignar)</label>
      </div>
      <p className="text-xs text-ink-muted">Los cambios aplican de inmediato a las {plan.subscribers} empresa{plan.subscribers === 1 ? '' : 's'} con este plan y quedan en la bitácora.</p>
      {save.isError && <Alert tone="danger">{getErrorMessage(save.error)}</Alert>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>Cancelar</Button>
        <Button type="submit" loading={save.isPending}>Guardar plan</Button>
      </div>
    </form>
  )
}

export default function PlatformPlansPage() {
  const { data, isLoading } = useQuery({ queryKey: ['platform', 'plans'], queryFn: platformApi.plans })
  const [editing, setEditing] = useState<PlatformPlan | null>(null)
  return (
    <Page>
      <PageHeader title="Planes" description="Qué incluye cada plan y cuánto permite. Son datos: se cambian aquí, sin desplegar código." />
      {isLoading || !data ? <div className="grid gap-4 md:grid-cols-3">{[1, 2, 3].map((i) => <Skeleton key={i} height={280} />)}</div> : (
        <div className="grid gap-4 md:grid-cols-3">
          {data.map((p) => (
            <Card key={p.id} className={cn('flex flex-col', !p.is_active && 'opacity-60')}>
              <div className="px-5 pt-5 flex items-start justify-between gap-2">
                <div><p className="text-base font-semibold text-ink">{p.name}</p><p className="text-xs text-ink-muted">{p.code}{!p.is_public && ' · oculto'}{!p.is_active && ' · inactivo'}</p></div>
                <Button size="sm" variant="ghost" icon={<Pencil size={14} />} onClick={() => setEditing(p)} aria-label={`Editar ${p.name}`} />
              </div>
              <p className="px-5 mt-3 text-2xl font-semibold text-ink num">{p.price_monthly ? formatCOP(p.price_monthly) : <span className="text-base text-ink-muted font-normal">Precio por definir</span>}
                {p.price_monthly && <span className="text-sm font-normal text-ink-muted"> / mes</span>}</p>
              {p.description && <p className="px-5 mt-1 text-sm text-ink-muted">{p.description}</p>}
              <ul className="px-5 mt-4 space-y-1.5 text-sm">
                {Object.entries(LIMIT_LABELS).map(([k, label]) => (
                  <li key={k} className="flex justify-between"><span className="text-ink-muted">{label}</span>
                    <span className="num text-ink">{p.limits[k] === null ? 'Ilimitado' : p.limits[k] ?? 0}</span></li>
                ))}
              </ul>
              <ul className="px-5 mt-4 space-y-1 text-sm flex-1">
                {Object.entries(FEATURE_LABELS).map(([k, label]) => (
                  <li key={k} className={cn('flex items-center gap-2', p.features.includes(k) ? 'text-ink' : 'text-ink-subtle line-through')}>
                    <Check size={14} className={p.features.includes(k) ? 'text-success' : 'opacity-0'} />{label}</li>
                ))}
              </ul>
              <p className="px-5 py-3 mt-4 border-t border-line text-xs text-ink-muted">{p.subscribers} empresa{p.subscribers === 1 ? '' : 's'} con este plan</p>
            </Card>
          ))}
        </div>
      )}
      <Modal title={editing ? `Plan ${editing.name}` : ''} isOpen={editing !== null} onClose={() => setEditing(null)} size="lg">
        {editing && <PlanForm plan={editing} onDone={() => setEditing(null)} />}
      </Modal>
    </Page>
  )
}
