'use client'

import { RotateCwIcon, TriangleAlertIcon } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function AppError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div role="alert" className="flex flex-1 flex-col items-center justify-center gap-5 py-16 text-center">
      <span className="flex size-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <TriangleAlertIcon className="size-6" aria-hidden="true" />
      </span>
      <div className="flex max-w-md flex-col gap-2">
        <h1 className="text-xl font-semibold tracking-tight">This page didn&apos;t load</h1>
        <p className="text-sm text-pretty text-muted-foreground">
          Your records are safe — nothing was changed. Try again, or head back home.
        </p>
        {error.digest && <p className="font-mono text-xs text-muted-foreground">{`Reference: ${error.digest}`}</p>}
      </div>
      <div className="flex gap-2">
        <Button onClick={reset}>
          <RotateCwIcon data-icon="inline-start" aria-hidden="true" />
          Try again
        </Button>
        <Button variant="outline" render={<Link href="/" />} nativeButton={false}>
          Go home
        </Button>
      </div>
    </div>
  )
}
