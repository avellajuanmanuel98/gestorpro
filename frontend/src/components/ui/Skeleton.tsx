interface SkeletonProps {
  className?: string
  width?:     string | number
  height?:    string | number
  rounded?:   'sm' | 'md' | 'lg' | 'full'
}

const roundedMap = {
  sm:   'rounded',
  md:   'rounded-lg',
  lg:   'rounded-xl',
  full: 'rounded-full',
}

export function Skeleton({ className = '', width, height, rounded = 'md' }: SkeletonProps) {
  return (
    <div
      className={['skeleton', roundedMap[rounded], className].filter(Boolean).join(' ')}
      style={{ width, height: height ?? 16 }}
      aria-hidden="true"
    />
  )
}

export function SkeletonCard() {
  return (
    <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-6 space-y-4 animate-pulse">
      <div className="flex items-center gap-3">
        <Skeleton width={40} height={40} rounded="lg" />
        <div className="space-y-2 flex-1">
          <Skeleton height={14} width="60%" />
          <Skeleton height={12} width="40%" />
        </div>
      </div>
      <Skeleton height={32} width="70%" />
      <Skeleton height={12} width="50%" />
    </div>
  )
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-6 py-4">
          <Skeleton width={32} height={32} rounded="full" />
          <div className="flex-1 space-y-2">
            <Skeleton height={13} width="40%" />
            <Skeleton height={11} width="25%" />
          </div>
          <Skeleton height={24} width={64} rounded="full" />
          <Skeleton height={28} width={60} />
        </div>
      ))}
    </div>
  )
}

export function SkeletonText({ lines = 3 }: { lines?: number }) {
  const widths = ['100%', '85%', '70%', '90%', '60%']
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} height={13} width={widths[i % widths.length]} />
      ))}
    </div>
  )
}
