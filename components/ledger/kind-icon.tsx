import { BoxesIcon, BoxIcon, HandCoinsIcon, LandmarkIcon, SendIcon, ShieldCheckIcon, TruckIcon, type LucideIcon } from 'lucide-react'
import { kindLabels } from '@/lib/ledger/format'
import type { ActivityKind } from '@/lib/ledger/types'
import { cn } from '@/lib/utils'

export const kindIcons: Record<ActivityKind, LucideIcon> = {
  payment: SendIcon,
  finance: LandmarkIcon,
  loan: HandCoinsIcon,
  product: BoxIcon,
  asset: LandmarkIcon,
  inventory: BoxesIcon,
  shipment: TruckIcon,
  blockchain: ShieldCheckIcon,
}

export function KindIcon({ kind, className }: { kind: ActivityKind; className?: string }) {
  const Icon = kindIcons[kind]
  return (
    <span
      className={cn(
        'flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-foreground',
        className,
      )}
    >
      <Icon className="size-4" aria-hidden="true" />
      <span className="sr-only">{kindLabels[kind]}</span>
    </span>
  )
}
