import { cn } from '@/lib/cn'
import Pagination from './Pagination'
import { SkeletonTable } from './Skeleton'
import type { PaginatedResponse } from '@/types'

export interface Column<T> {
  key: string
  header: string
  cell: (row: T) => React.ReactNode
  /** Cifras y montos: a la derecha y con dígitos tabulares */
  align?: 'left' | 'right'
  className?: string
  /** En móvil, la columna principal es el título de la tarjeta */
  primary?: boolean
  hideOnMobile?: boolean
}

interface DataTableProps<T> {
  columns: Column<T>[]
  rows: T[] | undefined
  rowKey: (row: T) => string | number
  isLoading?: boolean
  /** Estado vacío (con o sin filtros) */
  empty: React.ReactNode
  caption: string
  rowActions?: (row: T) => React.ReactNode
  onRowClick?: (row: T) => void
  pagination?: {
    data: Pick<PaginatedResponse<unknown>, 'count' | 'page' | 'page_size' | 'total_pages'> | undefined
    onPageChange: (page: number) => void
    noun: string
    isFetching?: boolean
  }
}

/**
 * Tabla estándar: carga con skeleton, estado vacío, paginación del servidor,
 * cifras alineadas a la derecha y, en móvil, tarjetas en lugar de scroll horizontal.
 */
export default function DataTable<T>({
  columns, rows, rowKey, isLoading, empty, caption, rowActions, onRowClick, pagination,
}: DataTableProps<T>) {
  const primary = columns.find((c) => c.primary) ?? columns[0]

  return (
    <div className="bg-surface border border-line rounded-xl overflow-hidden">
      {isLoading ? (
        <SkeletonTable rows={6} columns={Math.min(columns.length, 5)} />
      ) : !rows?.length ? (
        empty
      ) : (
        <>
          {/* Escritorio */}
          <table className="hidden md:table w-full text-sm">
            <caption className="sr-only">{caption}</caption>
            <thead>
              <tr className="border-b border-line bg-surface-muted/60">
                {columns.map((c) => (
                  <th key={c.key} scope="col"
                      className={cn('px-5 py-2.5 text-xs font-medium text-ink-muted whitespace-nowrap',
                        c.align === 'right' ? 'text-right' : 'text-left')}>
                    {c.header}
                  </th>
                ))}
                {rowActions && <th scope="col" className="px-5 py-2.5"><span className="sr-only">Acciones</span></th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.map((row) => (
                <tr key={rowKey(row)} onClick={onRowClick ? () => onRowClick(row) : undefined}
                    className={cn('group hover:bg-surface-muted/60 transition-colors', onRowClick && 'cursor-pointer')}>
                  {columns.map((c) => (
                    <td key={c.key} className={cn('px-5 py-3 text-ink align-middle',
                      c.align === 'right' && 'text-right num whitespace-nowrap', c.className)}>
                      {c.cell(row)}
                    </td>
                  ))}
                  {rowActions && (
                    <td className="px-5 py-3 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                      {rowActions(row)}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>

          {/* Móvil */}
          <ul className="md:hidden divide-y divide-line">
            {rows.map((row) => (
              <li key={rowKey(row)} className="px-4 py-3" onClick={onRowClick ? () => onRowClick(row) : undefined}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 font-medium text-ink">{primary.cell(row)}</div>
                  {rowActions && <div className="shrink-0" onClick={(e) => e.stopPropagation()}>{rowActions(row)}</div>}
                </div>
                <dl className="mt-1.5 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  {columns.filter((c) => c !== primary && !c.hideOnMobile).map((c) => (
                    <div key={c.key} className="min-w-0">
                      <dt className="text-ink-subtle">{c.header}</dt>
                      <dd className={cn('text-ink truncate', c.align === 'right' && 'num')}>{c.cell(row)}</dd>
                    </div>
                  ))}
                </dl>
              </li>
            ))}
          </ul>
        </>
      )}
      {pagination && <Pagination {...pagination} />}
    </div>
  )
}
