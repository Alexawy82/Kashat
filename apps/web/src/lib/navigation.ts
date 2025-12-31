import {
  LayoutDashboard,
  CreditCard,
  Calendar,
  PiggyBank,
  Upload,
  Settings,
  Repeat,
  ArrowRightLeft,
  Wallet,
  Building2,
  type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  href: string
  label: string
  icon: LucideIcon
}

/**
 * Main navigation items - used by Sidebar and MobileNav
 * Keep these in sync to prevent navigation drift
 */
export const MAIN_NAV_ITEMS: NavItem[] = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/accounts', label: 'Accounts', icon: Building2 },
  { href: '/networth', label: 'Net Worth', icon: Wallet },
  { href: '/transactions', label: 'Transactions', icon: CreditCard },
  { href: '/import', label: 'Import', icon: Upload },
  { href: '/bills', label: 'Bills', icon: Calendar },
  { href: '/subscriptions', label: 'Subscriptions', icon: Repeat },
  { href: '/budget', label: 'Budget', icon: PiggyBank },
  { href: '/transfers', label: 'Transfers', icon: ArrowRightLeft },
  { href: '/settings', label: 'Settings', icon: Settings },
]

/**
 * Quick access items for bottom nav (mobile) - subset of main nav
 * These are the most frequently used items
 */
export const BOTTOM_NAV_ITEMS: NavItem[] = [
  { href: '/', label: 'Home', icon: LayoutDashboard },
  { href: '/transactions', label: 'Transactions', icon: CreditCard },
  { href: '/bills', label: 'Bills', icon: Calendar },
  { href: '/budget', label: 'Budget', icon: PiggyBank },
]

/**
 * Command palette items - quick navigation
 */
export const COMMAND_PALETTE_ITEMS: NavItem[] = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/transactions', label: 'Transactions', icon: CreditCard },
  { href: '/settings', label: 'Settings', icon: Settings },
  { href: '/settings/system', label: 'System Health', icon: Settings },
]
