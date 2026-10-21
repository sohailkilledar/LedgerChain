'use client'

import { ThemeProvider as NextThemesProvider } from 'next-themes'

export type ThemeChoice = 'light' | 'dark' | 'system'

/** Single source of truth for Light / Dark / System. Adds `.dark` to <html>. */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      themes={['light', 'dark']}
      disableTransitionOnChange
    >
      {children}
    </NextThemesProvider>
  )
}
