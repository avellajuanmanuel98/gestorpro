import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, FileSpreadsheet, Upload } from 'lucide-react'
import { importApi, type ImportPreview, type ItemGroup } from '@/api/catalog'
import Alert from '@/components/ui/Alert'
import Button from '@/components/ui/Button'
import StatusMark from '@/components/ui/StatusMark'
import type { StatusSpec } from '@/components/ui/StatusMark'
import { formatQty } from '@/lib/catalog'
import { downloadFile } from '@/lib/download'
import { getErrorMessage } from '@/lib/errors'
import { formatCOP } from '@/lib/money'
import { useVocabulary } from '@/lib/vocabulary'
import { toast } from '@/store/toastStore'

const ROW_STATUS: Record<'new' | 'exists' | 'error', StatusSpec> = {
  new: { label: 'Nuevo', tone: 'success', glyph: 'solid' },
  exists: { label: 'Ya existe', tone: 'neutral', glyph: 'hollow' },
  error: { label: 'Revisar', tone: 'danger', glyph: 'paused' },
}

/**
 * Importar desde Excel en dos pasos: vista previa (no guarda nada) y confirmación
 * (crea solo las filas nuevas y válidas, todas juntas o ninguna).
 */
export default function ImportDialog({ group, onDone }: { group: ItemGroup; onDone: () => void }) {
  const queryClient = useQueryClient()
  const v = useVocabulary()
  const noun = group === 'products' ? 'productos' : v.ingredients
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const check = useMutation({ mutationFn: (f: File) => importApi.preview(group, f), onSuccess: setPreview })
  const confirm = useMutation({
    mutationFn: () => importApi.confirm(group, file!),
    onSuccess: (r) => {
      void queryClient.invalidateQueries({ queryKey: ['items'] })
      void queryClient.invalidateQueries({ queryKey: ['categories'] })
      toast.success(`${r.created} ${noun} importados${r.exists ? ` · ${r.exists} ya existían` : ''}`)
      onDone()
    },
  })
  const pick = (f: File | undefined) => {
    if (!f) return
    setFile(f); setPreview(null); check.mutate(f)
  }
  const s = preview?.summary
  return (
    <div className="space-y-4">
      {!preview && (
        <>
          <ol className="space-y-2 text-sm text-ink">
            <li>1. Descarga la plantilla y llénala: una fila por ítem. Solo el nombre es obligatorio.</li>
            <li>2. El precio va <strong>sin IVA</strong>; la existencia entra como saldo inicial.</li>
            <li>3. Súbela: verás qué se va a crear antes de confirmar.</li>
          </ol>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" icon={<Download size={14} />}
                    onClick={() => void downloadFile('/catalog/import/', { group }, 'plantilla.xlsx').catch((e) => toast.error(getErrorMessage(e)))}>
              Descargar plantilla
            </Button>
          </div>
          <label className="flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-line-strong p-8 text-center cursor-pointer hover:bg-surface-muted/60"
                 onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); pick(e.dataTransfer.files[0]) }}>
            <FileSpreadsheet size={26} className="text-ink-subtle" aria-hidden />
            <span className="text-sm text-ink">{check.isPending ? 'Revisando el archivo…' : 'Arrastra el archivo aquí o haz clic para elegirlo'}</span>
            <span className="text-xs text-ink-muted">Excel (.xlsx) o CSV · hasta 2.000 filas</span>
            <input type="file" accept=".xlsx,.csv" className="sr-only" onChange={(e) => pick(e.target.files?.[0])} />
          </label>
          {check.isError && <Alert tone="danger">{getErrorMessage(check.error)}</Alert>}
        </>
      )}

      {preview && s && (
        <>
          <p className="text-sm text-ink">
            <strong>{file?.name}</strong>: {s.new} nuevos, {s.exists} ya existen (se omiten), {s.error} con errores (se omiten).
          </p>
          {preview.new_categories.length > 0 && (
            <p className="text-xs text-ink-muted">Se crearán las categorías: {preview.new_categories.join(', ')}.</p>
          )}
          {preview.costs_ignored && <Alert tone="info">Tu rol no registra costos: la columna de costo se ignora.</Alert>}
          <div className="max-h-80 overflow-auto rounded-xl border border-line">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-surface-muted text-xs text-ink-muted"><tr>
                <th className="text-left font-medium py-2 px-3">Fila</th><th className="text-left font-medium py-2 px-3">Nombre</th>
                <th className="text-right font-medium py-2 px-3">Precio</th><th className="text-right font-medium py-2 px-3">Existencia</th>
                <th className="text-left font-medium py-2 px-3">Estado</th></tr></thead>
              <tbody className="divide-y divide-line">
                {preview.rows.map((r) => (
                  <tr key={r.line} className={r.status === 'error' ? 'bg-danger-soft/40' : undefined}>
                    <td className="py-1.5 px-3 text-ink-muted num">{r.line}</td>
                    <td className="py-1.5 px-3 text-ink">{r.name || '—'}
                      {r.errors.map((e) => <span key={e} className="block text-xs text-danger">{e}</span>)}</td>
                    <td className="py-1.5 px-3 text-right num">{r.price ? formatCOP(r.price) : '—'}</td>
                    <td className="py-1.5 px-3 text-right num">{r.stock ? formatQty(r.stock, r.unit) : '—'}</td>
                    <td className="py-1.5 px-3"><StatusMark status={ROW_STATUS[r.status]} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {s.error > 0 && <p className="text-xs text-ink-muted">Puedes corregir el archivo y volver a subirlo, o importar ahora solo los válidos.</p>}
          {confirm.isError && <Alert tone="danger">{getErrorMessage(confirm.error)}</Alert>}
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="ghost" onClick={() => { setPreview(null); setFile(null) }} icon={<Upload size={14} />}>Subir otro archivo</Button>
            <Button onClick={() => confirm.mutate()} loading={confirm.isPending} disabled={s.new === 0}>
              Importar {s.new} {noun}
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
