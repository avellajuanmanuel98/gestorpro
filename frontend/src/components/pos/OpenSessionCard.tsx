import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Wallet } from 'lucide-react'
import { cashApi } from '@/api/pos'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import { getErrorMessage } from '@/lib/errors'
import { toast } from '@/store/toastStore'

/** Apertura de turno: elegir caja (si hay varias) y contar la base inicial. */
export default function OpenSessionCard({ title = 'Abre la caja para empezar a vender' }: { title?: string }) {
  const queryClient = useQueryClient()
  const registers = useQuery({ queryKey: ['cash-registers'], queryFn: cashApi.registers })
  const [registerId, setRegisterId] = useState<string>('')
  const [amount, setAmount] = useState('')
  const free = registers.data?.filter((r) => !r.open_session_by) ?? []
  const selected = registerId || (free[0] ? String(free[0].id) : '')

  const open = useMutation({
    mutationFn: () => cashApi.open(Number(selected), amount.replace(/\./g, '').replace(',', '.') || '0'),
    onSuccess: (session) => {
      queryClient.setQueryData(['cash-current'], session)
      queryClient.invalidateQueries({ queryKey: ['cash-registers'] })
      toast.success(`${session.register_name} abierta`)
    },
  })

  return (
    <div className="max-w-md mx-auto mt-10 bg-surface border border-line rounded-2xl p-6 space-y-5">
      <div className="flex items-center gap-3">
        <span className="w-11 h-11 rounded-xl bg-accent-soft text-accent-ink flex items-center justify-center"><Wallet size={20} /></span>
        <div>
          <h2 className="text-base font-semibold text-ink">{title}</h2>
          <p className="text-sm text-ink-muted">Cuenta el efectivo con el que empiezas el turno.</p>
        </div>
      </div>
      {registers.data && free.length === 0 ? (
        <Alert tone="warning">Todas las cajas tienen un turno abierto. Pide que cierren una o crea otra caja.</Alert>
      ) : (
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); open.mutate() }}>
          {free.length > 1 && (
            <Select label="Caja" value={selected} onChange={(e) => setRegisterId(e.target.value)}>
              {free.map((r) => <option key={r.id} value={r.id}>{r.name} · {r.location_name}</option>)}
            </Select>
          )}
          <Input label="Base inicial en efectivo" inputMode="numeric" autoFocus placeholder="0" value={amount}
                 onChange={(e) => setAmount(e.target.value)} hint="Billetes y monedas que hay en el cajón al empezar." />
          {open.isError && <Alert tone="danger">{getErrorMessage(open.error)}</Alert>}
          <Button type="submit" size="lg" fullWidth loading={open.isPending} disabled={!selected}>Abrir caja</Button>
        </form>
      )}
    </div>
  )
}
