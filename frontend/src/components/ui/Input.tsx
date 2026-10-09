import { forwardRef, useId } from 'react'
import { cn } from '@/lib/cn'
import { controlClass, readOnlyClass, errorClass, hintClass, labelClass } from './field'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, hint, leftIcon, rightIcon, className = '', id, ...props }, ref) => {
    const generatedId = useId()
    const inputId = id ?? generatedId
    const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined
    return (
      <div className="space-y-1.5">
        {label && (
          <label htmlFor={inputId} className={labelClass}>
            {label}
            {props.required && <span className="text-danger ml-0.5" aria-hidden>*</span>}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-subtle pointer-events-none">{leftIcon}</span>
          )}
          <input
            ref={ref}
            id={inputId}
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy}
            className={cn(
              controlClass, readOnlyClass, 'h-9 px-3',
              error ? 'border-danger' : 'border-line-strong',
              !!leftIcon && 'pl-9', !!rightIcon && 'pr-9', className,
            )}
            {...props}
          />
          {rightIcon && <span className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-subtle">{rightIcon}</span>}
        </div>
        {error && <p id={`${inputId}-error`} className={errorClass}>{error}</p>}
        {!error && hint && <p id={`${inputId}-hint`} className={hintClass}>{hint}</p>}
      </div>
    )
  },
)

Input.displayName = 'Input'
export default Input
