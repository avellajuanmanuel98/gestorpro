import { forwardRef, useId } from 'react'
import { cn } from '@/lib/cn'
import { controlClass, errorClass, hintClass, labelClass } from './field'

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  hint?: string
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(({ label, error, hint, className = '', children, id, ...props }, ref) => {
  const generatedId = useId()
  const selectId = id ?? generatedId
  return (
    <div className="space-y-1.5">
      {label && (
        <label htmlFor={selectId} className={labelClass}>
          {label}
          {props.required && <span className="text-danger ml-0.5" aria-hidden>*</span>}
        </label>
      )}
      <select
        ref={ref}
        id={selectId}
        aria-invalid={error ? true : undefined}
        className={cn(controlClass, 'h-9 px-3', error ? 'border-danger' : 'border-line-strong', className)}
        {...props}
      >
        {children}
      </select>
      {error && <p className={errorClass}>{error}</p>}
      {!error && hint && <p className={hintClass}>{hint}</p>}
    </div>
  )
})

Select.displayName = 'Select'
export default Select
