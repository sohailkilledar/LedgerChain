import type { AccountPreferences, AccountProfile, AppNotification, SecurityOverview } from './types'

/**
 * Placeholder account data for the frontend prototype.
 * Only lib/ledger/service.ts reads this file.
 */
export const mockProfile: AccountProfile = {
  id: 'acct_7Q2M9KX4',
  name: 'Meera Kulkarni',
  company: 'Kulkarni Exports',
  email: 'meera@kulkarniexports.in',
  role: 'Account owner',
  phone: '+91 98200 41177',
  memberSince: '2025-03-14T09:00:00+05:30',
}

export const mockPreferences: AccountPreferences = {
  timeZone: 'Asia/Kolkata',
  dateFormat: 'dmy',
  showTechnicalByDefault: false,
  notifyPayments: true,
  notifySecurity: true,
  notifyProductUpdates: false,
  shareUsageData: false,
}

export const mockNotifications: AppNotification[] = [
  {
    id: 'ntf_01',
    category: 'payments',
    title: 'Payment confirmed',
    body: '₹18,000 to Arjun Textiles Pvt. Ltd. was recorded and confirmed.',
    createdAt: '2026-09-27T10:12:00+05:30',
    read: false,
    href: '/activity?record=act_01',
  },
  {
    id: 'ntf_02',
    category: 'account',
    title: 'A loan request needs a document',
    body: 'Upload your latest GST return so the lender can continue reviewing your request.',
    createdAt: '2026-09-26T16:40:00+05:30',
    read: false,
    href: '/activity',
  },
  {
    id: 'ntf_03',
    category: 'security',
    title: 'New sign-in from Chrome on Windows',
    body: 'Pune, Maharashtra. If this was not you, sign out other sessions from Security.',
    createdAt: '2026-09-25T08:05:00+05:30',
    read: false,
    href: '/security',
  },
  {
    id: 'ntf_04',
    category: 'payments',
    title: 'Payment didn’t go through',
    body: 'A payment to Sahyadri Logistics was stopped before any money moved. You can try again.',
    createdAt: '2026-09-22T12:30:00+05:30',
    read: true,
    href: '/activity',
  },
  {
    id: 'ntf_06',
    category: 'security',
    title: 'Password changed',
    body: 'Your LedgerChain password was updated. Other devices were asked to sign in again.',
    createdAt: '2026-08-30T19:22:00+05:30',
    read: true,
    href: '/security',
  },
]

export const mockSecurity: SecurityOverview = {
  passwordUpdatedAt: '2026-08-30T19:22:00+05:30',
  twoFactorEnabled: false,
  sessions: [
    {
      id: 'ses_current',
      device: 'MacBook Air',
      browser: 'Safari 19',
      location: 'Mumbai, Maharashtra',
      lastActiveAt: '2026-09-27T10:30:00+05:30',
      current: true,
    },
    {
      id: 'ses_02',
      device: 'Windows PC',
      browser: 'Chrome 141',
      location: 'Pune, Maharashtra',
      lastActiveAt: '2026-09-25T08:05:00+05:30',
      current: false,
    },
    {
      id: 'ses_03',
      device: 'iPhone 16',
      browser: 'LedgerChain for iOS',
      location: 'Mumbai, Maharashtra',
      lastActiveAt: '2026-09-21T21:47:00+05:30',
      current: false,
    },
  ],
  events: [
    {
      id: 'sev_01',
      title: 'Signed in',
      detail: 'Safari on MacBook Air · Mumbai',
      createdAt: '2026-09-27T09:02:00+05:30',
      tone: 'neutral',
    },
    {
      id: 'sev_02',
      title: 'New device signed in',
      detail: 'Chrome on Windows PC · Pune',
      createdAt: '2026-09-25T08:05:00+05:30',
      tone: 'warning',
    },
    {
      id: 'sev_03',
      title: 'Password changed',
      detail: 'Safari on MacBook Air · Mumbai',
      createdAt: '2026-08-30T19:22:00+05:30',
      tone: 'neutral',
    },
  ],
}
