'use client'

import { CheckIcon, CopyIcon } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'

export function CopyButton({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      setCopied(false)
    }
  }

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-xs"
      onClick={handleCopy}
      aria-label={copied ? `${label} copied` : `Copy ${label}`}
    >
      {copied ? <CheckIcon aria-hidden="true" /> : <CopyIcon aria-hidden="true" />}
      <span className="sr-only" aria-live="polite">
        {copied ? 'Copied' : ''}
      </span>
    </Button>
  )
}
