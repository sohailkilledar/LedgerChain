'use client'

import { CircleHelpIcon } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

/** A technical term with a plain-language explanation on hover or focus. */
export function TermHint({ term, explanation }: { term: string; explanation: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      {term}
      <Tooltip>
        <TooltipTrigger
          className="inline-flex size-4 items-center justify-center rounded-sm text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
          aria-label={`What is ${term}?`}
        >
          <CircleHelpIcon className="size-3.5" aria-hidden="true" />
        </TooltipTrigger>
        <TooltipContent>{explanation}</TooltipContent>
      </Tooltip>
    </span>
  )
}
