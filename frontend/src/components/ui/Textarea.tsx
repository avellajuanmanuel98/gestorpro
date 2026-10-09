import { forwardRef, useId } from 'react'
import { cn } from '@/lib/cn'
import { controlClass, readOnlyClass, errorClass, labelClass } from './field'

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(({ label, error, className = '', id, rows = 3, ...props }, ref) => {
  const generatedId = useId()
  const textareaId = id ?? generatedId
  return (
    <div className="space-y-1.5">
      {label && <label htmlFor={textareaId} className={labelClass}>{label}</label>}
      <textarea
        ref={ref}
        id={textareaId}
        rows={rows}
        aria-invalid={error ? true : undefined}
        className={cn(controlClass, readOnlyClass, 'px-3 py-2 resize-y', error ? 'border-danger' : 'border-line-strong', className)}
        {...props}
      />
      {error && <p className={errorClass}>{error}</p>}
    </div>
  )
})

Textarea.displayName = 'Textarea'
export default Textarea
