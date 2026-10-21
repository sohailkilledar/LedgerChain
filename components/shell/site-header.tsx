'use client'

import { MenuIcon } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { AccountMenu, type AccountSummary } from './account-menu'
import { AppNav } from './app-nav'
import { Logo } from './logo'

function SkipLink() {
  return (
    <a
      href="#main"
      className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:text-primary-foreground"
    >
      Skip to content
    </a>
  )
}

/** Persistent sidebar on large screens. */
export function SiteSidebar({ account }: { account: AccountSummary }) {
  return (
    <aside className="sticky top-0 hidden h-dvh w-64 shrink-0 flex-col gap-6 border-r bg-card px-5 py-5 lg:flex">
      <SkipLink />
      <div className="px-1">
        <Logo />
      </div>
      <div className="-mr-2 flex flex-1 flex-col overflow-y-auto pr-2">
        <AppNav />
      </div>
      <div className="-mx-2 border-t pt-3">
        <AccountMenu account={account} />
      </div>
    </aside>
  )
}

/** Compact top bar with a navigation sheet below the large breakpoint. */
export function SiteHeader({ account }: { account: AccountSummary }) {
  const [open, setOpen] = useState(false)

  return (
    <header className="sticky top-0 z-40 border-b bg-card lg:hidden">
      <SkipLink />
      <div className="flex h-14 items-center gap-3 px-4 md:px-6">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger render={<Button variant="ghost" size="icon-lg" className="-ml-2" aria-label="Open menu" />}>
            <MenuIcon aria-hidden="true" />
          </SheetTrigger>
          <SheetContent side="left" className="w-72 gap-0">
            <SheetHeader className="border-b">
              <SheetTitle className="sr-only">Menu</SheetTitle>
              <Logo />
            </SheetHeader>
            <div className="flex flex-1 flex-col overflow-y-auto px-4 py-5">
              <AppNav onNavigate={() => setOpen(false)} />
            </div>
            <div className="border-t p-2">
              <AccountMenu account={account} onNavigate={() => setOpen(false)} />
            </div>
          </SheetContent>
        </Sheet>
        <Logo />
        <div className="ml-auto">
          <AccountMenu account={account} compact side="bottom" />
        </div>
      </div>
    </header>
  )
}
