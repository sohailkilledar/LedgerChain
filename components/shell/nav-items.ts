import {
  BookOpenIcon,
  BoxIcon,
  BoxesIcon,
  HomeIcon,
  LandmarkIcon,
  LifeBuoyIcon,
  ListIcon,
  SendIcon,
  SettingsIcon,
  UserIcon,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  label: string
  icon: LucideIcon
  href: string
}

export interface NavGroup {
  label?: string
  items: NavItem[]
}

export const primaryNav: NavGroup[] = [
  {
    items: [
      { href: '/', label: 'Home', icon: HomeIcon },
      { href: '/activity', label: 'Activity', icon: ListIcon },
    ],
  },
  {
    label: 'Finance',
    items: [
      { href: '/finance', label: 'Finance operations', icon: LandmarkIcon },
      { href: '/payments/new', label: 'Payments', icon: SendIcon },
    ],
  },
  {
    label: 'Supply chain',
    items: [
      { href: '/products', label: 'Products', icon: BoxIcon },
      { href: '/inventory', label: 'Inventory', icon: BoxesIcon },
    ],
  },
  {
    label: 'Ownership',
    items: [{ href: '/assets', label: 'Assets', icon: LandmarkIcon }],
  },
]

export const secondaryNav: NavItem[] = [
  { href: '/how-it-works', label: 'How LedgerChain works', icon: BookOpenIcon },
  { href: '/help', label: 'Help & support', icon: LifeBuoyIcon },
]

export const accountNav: NavItem[] = [
  { href: '/profile', label: 'Profile', icon: UserIcon },
  { href: '/settings', label: 'Settings', icon: SettingsIcon },
]

export function isActive(pathname: string, href: string) {
  if (href.includes('#')) return false
  if (href === '/') return pathname === '/'
  return pathname.startsWith(href.split('/').slice(0, 2).join('/'))
}
