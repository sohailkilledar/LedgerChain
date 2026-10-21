import { CircleAlertIcon, CircleCheckIcon, CircleXIcon, ClockIcon, type LucideIcon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { statusLabels } from '@/lib/ledger/format'
import type { RecordStatus } from '@/lib/ledger/types'
import { cn } from '@/lib/utils'

export const statusIcons: Record<RecordStatus, LucideIcon> = {
  completed: CircleCheckIcon,
  pending: ClockIcon,
  failed: CircleXIcon,
  action_required: CircleAlertIcon,
}

export const statusToneClass: Record<RecordStatus, string> = {
  completed: 'bg-success-soft text-success',
  pending: 'bg-warning-soft text-warning',
  failed: 'bg-destructive-soft text-destructive',
  action_required: 'bg-info-soft text-info',
}

/** Status is always communicated by icon + text, never colour alone. */
export function StatusBadge({
  status,
  label,
  className,
}: {
  status: RecordStatus
  label?: string
  className?: string
}) {
  const Icon = statusIcons[status]
  return (
    <Badge variant="outline" className={cn('border-transparent', statusToneClass[status], className)}>
      <Icon data-icon="inline-start" aria-hidden="true" />
      {label ?? statusLabels[status]}
    </Badge>
  )
}
