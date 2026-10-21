import Link from 'next/link'
import { Fragment } from 'react'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'

export interface Crumb {
  label: string
  href?: string
}

export function PageHeader({
  title,
  eyebrow,
  description,
  breadcrumbs,
  actions,
}: {
  title: string
  eyebrow?: string
  description?: string
  breadcrumbs?: Crumb[]
  actions?: React.ReactNode
}) {
  return (
    <header className="flex flex-col gap-3">
      {breadcrumbs && breadcrumbs.length > 0 && (
        <Breadcrumb>
          <BreadcrumbList>
            {breadcrumbs.map((crumb, index) => (
              <Fragment key={crumb.label}>
                <BreadcrumbItem>
                  {crumb.href ? (
                    <BreadcrumbLink render={<Link href={crumb.href} />}>{crumb.label}</BreadcrumbLink>
                  ) : (
                    <BreadcrumbPage>{crumb.label}</BreadcrumbPage>
                  )}
                </BreadcrumbItem>
                {index < breadcrumbs.length - 1 && <BreadcrumbSeparator />}
              </Fragment>
            ))}
          </BreadcrumbList>
        </Breadcrumb>
      )}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex max-w-2xl flex-col gap-1.5">
          {eyebrow && <p className="text-xs font-medium text-muted-foreground">{eyebrow}</p>}
          <h1 className="text-2xl font-semibold tracking-tight text-balance md:text-[1.75rem]">{title}</h1>
          {description && <p className="text-pretty text-muted-foreground">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
      </div>
    </header>
  )
}
