'use client'

import { useEffect } from 'react'

const AUTHENTICATED_ROUTES = [
  '/',
  '/activity',
  '/assets',
  '/help',
  '/inventory',
  '/how-it-works',
  '/payments',
  '/products',
  '/profile',
  '/settings',
]

function isAuthenticatedRoute(pathname: string) {
  return AUTHENTICATED_ROUTES.some((route) => route === '/' ? pathname === '/' : pathname === route || pathname.startsWith(`${route}/`))
}

export function SessionHistoryGuard() {
  useEffect(() => {
    function reloadAuthenticatedPage() {
      if (!isAuthenticatedRoute(window.location.pathname)) return

      // Back/forward restoration can revive a protected page after the session cookie is cleared.
      document.documentElement.style.visibility = 'hidden'
      window.location.reload()
    }

    function handlePageShow(event: PageTransitionEvent) {
      if (event.persisted) reloadAuthenticatedPage()
    }

    window.addEventListener('popstate', reloadAuthenticatedPage)
    window.addEventListener('pageshow', handlePageShow)

    return () => {
      window.removeEventListener('popstate', reloadAuthenticatedPage)
      window.removeEventListener('pageshow', handlePageShow)
    }
  }, [])

  return null
}
