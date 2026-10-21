'use client'

import { ChevronDownIcon } from 'lucide-react'
import { useState } from 'react'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { cn } from '@/lib/utils'

export interface FaqItem {
  question: string
  answer: string
}

export function FaqList({ items }: { items: FaqItem[] }) {
  return (
    <div className="flex flex-col divide-y rounded-xl border bg-card">
      {items.map((item) => (
        <FaqRow key={item.question} item={item} />
      ))}
    </div>
  )
}

function FaqRow({ item }: { item: FaqItem }) {
  const [open, setOpen] = useState(false)
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <h3>
        <CollapsibleTrigger className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left text-sm font-medium outline-none transition-colors hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset">
          {item.question}
          <ChevronDownIcon
            aria-hidden="true"
            className={cn('size-4 shrink-0 text-muted-foreground transition-transform duration-200', open && 'rotate-180')}
          />
        </CollapsibleTrigger>
      </h3>
      <CollapsibleContent>
        <p className="max-w-2xl px-5 pb-4 text-sm leading-relaxed text-pretty text-muted-foreground">{item.answer}</p>
      </CollapsibleContent>
    </Collapsible>
  )
}
