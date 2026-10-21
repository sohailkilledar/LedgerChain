import { ArrowDownIcon, ArrowRightIcon, type LucideIcon } from 'lucide-react'
import { Fragment } from 'react'
import { cn } from '@/lib/utils'

export interface FlowStep {
  icon: LucideIcon
  title: string
  description?: string
}

/** Horizontal step flow on wide screens, vertical on mobile. The last step is emphasised as the outcome. */
export function FlowDiagram({
  steps,
  label,
  numbered = false,
  className,
}: {
  steps: FlowStep[]
  label: string
  numbered?: boolean
  className?: string
}) {
  return (
    <ol
      aria-label={label}
      className={cn('flex flex-col items-stretch gap-2 md:flex-row md:items-stretch md:gap-0', className)}
    >
      {steps.map((step, index) => {
        const Icon = step.icon
        const isLast = index === steps.length - 1
        return (
          <Fragment key={step.title}>
            <li
              className={cn(
                'flex flex-1 items-start gap-3 rounded-xl border bg-card p-4 md:flex-col md:gap-3',
                isLast && 'border-primary/40 bg-accent',
              )}
            >
              <span
                className={cn(
                  'flex size-10 shrink-0 items-center justify-center rounded-lg',
                  isLast ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground',
                )}
              >
                <Icon className="size-5" aria-hidden="true" />
              </span>
              <div className="flex flex-col gap-1">
                <span className="text-sm font-semibold">
                  {numbered && <span className="mr-1.5 text-muted-foreground tabular-nums">{index + 1}.</span>}
                  {step.title}
                </span>
                {step.description && (
                  <span className="text-xs leading-relaxed text-pretty text-muted-foreground">{step.description}</span>
                )}
              </div>
            </li>
            {!isLast && (
              <li aria-hidden="true" className="flex shrink-0 items-center justify-center text-muted-foreground md:px-1.5">
                <ArrowDownIcon className="size-4 md:hidden" />
                <ArrowRightIcon className="hidden size-4 md:block" />
              </li>
            )}
          </Fragment>
        )
      })}
    </ol>
  )
}
