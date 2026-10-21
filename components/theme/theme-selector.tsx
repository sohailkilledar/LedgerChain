'use client'

import { MonitorIcon, MoonIcon, SunIcon, type LucideIcon } from 'lucide-react'
import { useTheme } from 'next-themes'
import { useSyncExternalStore } from 'react'
import { cn } from '@/lib/utils'
import type { ThemeChoice } from './theme-provider'

export const themeOptions: { value: ThemeChoice; label: string; description: string; icon: LucideIcon }[] = [
  { value: 'light', label: 'Light', description: 'Bright surfaces for daytime work', icon: SunIcon },
  { value: 'dark', label: 'Dark', description: 'Low-glare surfaces for dim rooms', icon: MoonIcon },
  { value: 'system', label: 'System', description: 'Follow your device setting', icon: MonitorIcon },
]

const subscribe = () => () => {}

/** True only after hydration, so theme-dependent UI never mismatches the server render. */
export function useHydrated() {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  )
}

/** Radio-card theme picker used on the Settings page. */
export function ThemeSelector() {
  const { theme, setTheme } = useTheme()
  const hydrated = useHydrated()
  const current = hydrated ? (theme as ThemeChoice | undefined) : undefined

  return (
    <div role="radiogroup" aria-label="Theme" className="grid gap-3 sm:grid-cols-3">
      {themeOptions.map((option) => {
        const Icon = option.icon
        const selected = current === option.value
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => setTheme(option.value)}
            className={cn(
              'group/theme flex flex-col gap-3 rounded-xl border bg-card p-3 text-left outline-none transition-[border-color,box-shadow,background-color] hover:border-foreground/25 focus-visible:ring-3 focus-visible:ring-ring/50 active:translate-y-px',
              selected && 'border-primary ring-1 ring-primary hover:border-primary',
            )}
          >
            <ThemePreview variant={option.value} />
            <span className="flex items-start gap-2.5">
              <Icon className={cn('mt-0.5 size-4 shrink-0', selected ? 'text-primary' : 'text-muted-foreground')} aria-hidden="true" />
              <span className="flex flex-col gap-0.5">
                <span className="text-sm font-medium">{option.label}</span>
                <span className="text-xs text-muted-foreground">{option.description}</span>
              </span>
            </span>
          </button>
        )
      })}
    </div>
  )
}

/** Miniature, static rendering of the app shell in each theme. Decorative. */
function ThemePreview({ variant }: { variant: ThemeChoice }) {
  const light = (
    <div className="flex h-full flex-1 gap-1.5 bg-[oklch(0.982_0.003_247)] p-1.5">
      <div className="w-1/4 rounded-sm bg-white" />
      <div className="flex flex-1 flex-col gap-1">
        <div className="h-2 w-2/3 rounded-sm bg-[oklch(0.4_0.1_257)]" />
        <div className="flex-1 rounded-sm bg-white" />
      </div>
    </div>
  )
  const dark = (
    <div className="flex h-full flex-1 gap-1.5 bg-[oklch(0.165_0.012_257)] p-1.5">
      <div className="w-1/4 rounded-sm bg-[oklch(0.2_0.014_257)]" />
      <div className="flex flex-1 flex-col gap-1">
        <div className="h-2 w-2/3 rounded-sm bg-[oklch(0.74_0.1_257)]" />
        <div className="flex-1 rounded-sm bg-[oklch(0.2_0.014_257)]" />
      </div>
    </div>
  )

  return (
    <span aria-hidden="true" className="flex h-16 overflow-hidden rounded-md border">
      {variant === 'light' && light}
      {variant === 'dark' && dark}
      {variant === 'system' && (
        <>
          {light}
          {dark}
        </>
      )}
    </span>
  )
}
