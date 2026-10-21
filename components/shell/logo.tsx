import Link from 'next/link'

export function Logo() {
  return (
    <Link
      href="/"
      className="flex items-center gap-2 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <svg viewBox="0 0 24 24" className="size-7" aria-hidden="true">
        <rect width="24" height="24" rx="6" className="fill-primary" />
        <rect x="6" y="7" width="12" height="2.2" rx="1.1" className="fill-primary-foreground" />
        <rect x="6" y="11" width="8" height="2.2" rx="1.1" className="fill-primary-foreground/70" />
        <rect x="6" y="15" width="10" height="2.2" rx="1.1" className="fill-primary-foreground/45" />
      </svg>
      <span className="text-[0.9375rem] font-semibold tracking-tight">LedgerChain</span>
    </Link>
  )
}
