import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

/** Heading block shared by every auth screen. */
export function AuthHeading({
  title,
  description,
  icon: Icon,
  tone = 'primary',
}: {
  title: string
  description?: React.ReactNode
  icon?: LucideIcon
  tone?: 'primary' | 'success' | 'warning'
}) {
  return (
    <div className="flex flex-col gap-2">
      {Icon && (
        <span
          className={cn(
            'mb-2 flex size-11 animate-pop items-center justify-center rounded-full',
            tone === 'primary' && 'bg-accent text-primary',
            tone === 'success' && 'bg-success-soft text-success',
            tone === 'warning' && 'bg-warning-soft text-warning',
          )}
        >
          <Icon className="size-5" aria-hidden="true" />
        </span>
      )}
      <h1 className="text-2xl font-semibold tracking-tight text-balance">{title}</h1>
      {description && <p className="text-pretty text-muted-foreground">{description}</p>}
    </div>
  )
}


