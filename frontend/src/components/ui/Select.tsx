import { forwardRef, useId } from 'react'

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(({ label, error, className = '', children, id, ...props }, ref) => {
  const generatedId = useId()
  const selectId = id ?? generatedId
  return (
  <div className="space-y-1.5">
    {label && (
      <label htmlFor={selectId} className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">{label}</label>
    )}
    <select
      ref={ref}
      id={selectId}
      aria-invalid={error ? true : undefined}
      className={[
        'w-full h-9 rounded-lg border bg-white dark:bg-zinc-900/50 px-3 text-sm',
        'text-zinc-900 dark:text-zinc-100',
        'focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        error ? 'border-red-400 dark:border-red-500' : 'border-zinc-200 dark:border-zinc-700',
        className,
      ].join(' ')}
      {...props}
    >
      {children}
    </select>
    {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}
  </div>
  )
})

Select.displayName = 'Select'
export default Select
