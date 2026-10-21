'use client'

import { CheckIcon, CircleIcon, EyeIcon, EyeOffIcon } from 'lucide-react'
import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { passwordChecks, passwordStrength } from '@/lib/validation'

/** Password field with an accessible show/hide toggle. */
export function PasswordInput({ className, ...props }: Omit<React.ComponentProps<typeof Input>, 'type'>) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="relative">
      <Input {...props} type={visible ? 'text' : 'password'} className={cn('pr-11', className)} />
      <button
        type="button"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? 'Hide password' : 'Show password'}
        aria-pressed={visible}
        aria-controls={props.id}
        className="absolute inset-y-0 right-0 flex w-10 items-center justify-center rounded-r-md text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
      >
        {visible ? <EyeOffIcon className="size-4" aria-hidden="true" /> : <EyeIcon className="size-4" aria-hidden="true" />}
      </button>
    </div>
  )
}

const strengthCopy = {
  empty: { label: '', bars: 0, tone: 'bg-muted' },
  weak: { label: 'Weak', bars: 1, tone: 'bg-destructive' },
  fair: { label: 'Fair', bars: 2, tone: 'bg-warning' },
  strong: { label: 'Strong', bars: 3, tone: 'bg-success' },
} as const

/** Live strength meter plus the checklist behind it. */
export function PasswordStrengthMeter({ password, id }: { password: string; id?: string }) {
  const strength = passwordStrength(password)
  const copy = strengthCopy[strength]
  const checks = passwordChecks(password)

  return (
    <div id={id} className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <div className="flex flex-1 gap-1" aria-hidden="true">
          {[1, 2, 3].map((bar) => (
            <span
              key={bar}
              className={cn('h-1 flex-1 rounded-full transition-colors duration-300', bar <= copy.bars ? copy.tone : 'bg-muted')}
            />
          ))}
        </div>
        <span className="w-12 text-right text-xs font-medium text-muted-foreground" aria-live="polite">
          {copy.label && <span className="sr-only">Password strength: </span>}
          {copy.label}
        </span>
      </div>
      <ul className="grid gap-1 text-xs sm:grid-cols-2">
        {checks.map((check) => (
          <li
            key={check.id}
            className={cn('flex items-center gap-1.5 transition-colors', check.met ? 'text-success' : 'text-muted-foreground')}
          >
            {check.met ? (
              <CheckIcon className="size-3.5 shrink-0" aria-hidden="true" />
            ) : (
              <CircleIcon className="size-3 shrink-0 opacity-60" aria-hidden="true" />
            )}
            <span>
              {check.label}
              <span className="sr-only">{check.met ? ' — done' : ' — not yet'}</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
