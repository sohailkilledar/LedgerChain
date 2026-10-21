import { cn } from '@/lib/utils'

/** Two-column section: heading on the left, card content on the right (stacked on mobile). */
export function SettingsSection({
  id,
  title,
  description,
  children,
  className,
}: {
  id?: string
  title: string
  description?: string
  children: React.ReactNode
  className?: string
}) {
  const headingId = id ? `${id}-heading` : undefined
  return (
    <section
      id={id}
      aria-labelledby={headingId}
      className={cn('grid scroll-mt-24 gap-4 md:grid-cols-[14rem_minmax(0,1fr)] md:gap-8 lg:grid-cols-[16rem_minmax(0,1fr)]', className)}
    >
      <div className="flex flex-col gap-1">
        <h2 id={headingId} className="text-base font-semibold">
          {title}
        </h2>
        {description && <p className="text-sm text-pretty text-muted-foreground">{description}</p>}
      </div>
      <div className="min-w-0 rounded-xl border bg-card">{children}</div>
    </section>
  )
}

/** A labelled row inside a SettingsSection card. */
export function SettingRow({
  title,
  description,
  htmlFor,
  children,
}: {
  title: string
  description?: React.ReactNode
  htmlFor?: string
  children?: React.ReactNode
}) {
  const Title = htmlFor ? 'label' : 'p'
  return (
    <div className="flex flex-col gap-3 border-b p-4 last:border-b-0 sm:flex-row sm:items-center sm:justify-between sm:gap-6 md:px-5">
      <div className="flex min-w-0 flex-col gap-0.5">
        <Title htmlFor={htmlFor} className="text-sm font-medium">
          {title}
        </Title>
        {description && <div className="text-sm text-pretty text-muted-foreground">{description}</div>}
      </div>
      {children && <div className="flex shrink-0 items-center gap-2">{children}</div>}
    </div>
  )
}

