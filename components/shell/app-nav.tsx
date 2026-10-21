'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { isActive, primaryNav, secondaryNav, type NavItem } from './nav-items'

function NavLink({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const pathname = usePathname()
  const Icon = item.icon
  const active = isActive(pathname, item.href)
  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'group/nav relative flex h-9 items-center gap-3 rounded-md px-2.5 text-sm font-medium text-muted-foreground outline-none transition-colors hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring',
        active && 'bg-accent text-accent-foreground hover:bg-accent hover:text-accent-foreground',
      )}
    >
      {active && (
        <span aria-hidden="true" className="absolute inset-y-2 -left-3 w-0.5 rounded-full bg-primary" />
      )}
      <Icon
        className={cn('size-4 transition-colors', active ? 'text-primary' : 'group-hover/nav:text-foreground')}
        aria-hidden="true"
      />
      <span className="flex-1 truncate">{item.label}</span>
    </Link>
  )
}

/** Shared navigation used by the desktop sidebar and the mobile sheet. */
export function AppNav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex flex-1 flex-col gap-6">
      <nav aria-label="Main" className="flex flex-col gap-5">
        {primaryNav.map((group, index) => (
          <div key={group.label ?? index} className="flex flex-col gap-1">
            {group.label && (
              <h2 className="px-2.5 pb-1 text-[0.6875rem] font-semibold uppercase tracking-wider text-muted-foreground">
                {group.label}
              </h2>
            )}
            <ul className="flex flex-col gap-0.5">
              {group.items.map((item) => (
                <li key={item.label}>
                  <NavLink item={item} onNavigate={onNavigate} />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <nav aria-label="Help and resources" className="mt-auto flex flex-col gap-1 border-t pt-4">
        <ul className="flex flex-col gap-0.5">
          {secondaryNav.map((item) => (
            <li key={item.label}>
              <NavLink item={item} onNavigate={onNavigate} />
            </li>
          ))}
        </ul>
      </nav>
    </div>
  )
}
