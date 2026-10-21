'use client'

import { ChevronsUpDownIcon, LifeBuoyIcon, LogOutIcon } from 'lucide-react'
import { useTheme } from 'next-themes'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { themeOptions, useHydrated } from '@/components/theme/theme-selector'
import { ledgerService } from '@/lib/ledger/service'
import { cn } from '@/lib/utils'
import { accountNav } from './nav-items'

export interface AccountSummary {
  name: string
  company: string
  email: string
}

export function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('')
}

export function AccountMenu({
  account,
  compact = false,
  side = 'top',
  onNavigate,
}: {
  account: AccountSummary
  compact?: boolean
  side?: 'top' | 'bottom'
  onNavigate?: () => void
}) {
  const router = useRouter()
  const { theme, setTheme } = useTheme()
  const hydrated = useHydrated()

  function go(href: string) {
    onNavigate?.()
    router.push(href)
  }

  async function signOut() {
    onNavigate?.()
    try {
      await ledgerService.signOut()
      toast.success('You have been signed out.')
      router.replace('/login')
    } catch (error) {
      toast.error('Could not sign out', {
        description: error instanceof Error ? error.message : 'Please try again.',
      })
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={`Account menu for ${account.name}`}
        className={cn(
          'flex min-w-0 items-center gap-2.5 rounded-lg text-left outline-none transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring data-[popup-open]:bg-muted',
          compact ? 'p-1' : 'w-full p-2',
        )}
      >
        <span className="relative">
          <Avatar className="size-8">
            <AvatarFallback className="bg-accent text-xs font-semibold text-accent-foreground">
              {initials(account.name)}
            </AvatarFallback>
          </Avatar>
        </span>
        {!compact && (
          <>
            <span className="flex min-w-0 flex-1 flex-col leading-tight">
              <span className="truncate text-sm font-medium">{account.name}</span>
              <span className="truncate text-xs text-muted-foreground">{account.company}</span>
            </span>
            <ChevronsUpDownIcon className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          </>
        )}
      </DropdownMenuTrigger>
      <DropdownMenuContent side={side} align={compact ? 'end' : 'start'} className="w-60">
        <DropdownMenuGroup>
          <DropdownMenuLabel className="flex flex-col gap-0.5 py-2">
            <span className="truncate text-sm font-medium text-foreground">{account.name}</span>
            <span className="truncate text-xs font-normal">{account.email}</span>
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          {accountNav.map((item) => {
            const Icon = item.icon
            return (
              <DropdownMenuItem key={item.href} onClick={() => go(item.href)}>
                <Icon aria-hidden="true" />
                <span className="flex-1">{item.label}</span>
              </DropdownMenuItem>
            )
          })}
          <DropdownMenuItem onClick={() => go('/help')}>
            <LifeBuoyIcon aria-hidden="true" />
            Help & support
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuLabel>Theme</DropdownMenuLabel>
          <DropdownMenuRadioGroup value={hydrated ? (theme ?? 'system') : 'system'} onValueChange={(value) => setTheme(value as string)}>
            {themeOptions.map((option) => {
              const Icon = option.icon
              return (
                <DropdownMenuRadioItem key={option.value} value={option.value}>
                  <Icon aria-hidden="true" />
                  {option.label}
                </DropdownMenuRadioItem>
              )
            })}
          </DropdownMenuRadioGroup>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={signOut}>
          <LogOutIcon aria-hidden="true" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
