import { cn } from '@/lib/cn'

interface SkeletonProps {
  className?: string
  width?: string | number
  height?: string | number
}

export function Skeleton({ className, width, height = 14 }: SkeletonProps) {
  return <div className={cn('skeleton', className)} style={{ width, height }} aria-hidden="true" />
}

export function SkeletonTable({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div role="status" aria-label="Cargando" className="divide-y divide-line">
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex items-center gap-6 px-5 py-3.5">
          {Array.from({ length: columns }).map((__, c) => (
            <Skeleton key={c} height={12} width={c === 0 ? '28%' : `${12 + ((r + c) % 3) * 6}%`} />
          ))}
        </div>
      ))}
    </div>
  )
}

export function SkeletonText({ lines = 3 }: { lines?: number }) {
  const widths = ['100%', '85%', '70%', '90%', '60%']
  return (
    <div className="space-y-2" aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => <Skeleton key={i} height={12} width={widths[i % widths.length]} />)}
    </div>
  )
}
