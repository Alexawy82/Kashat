'use client'

import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  CreditCard,
  Repeat,
  ArrowRightLeft,
  Settings,
  Search,
  Upload,
} from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const navItems = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Transactions', href: '/transactions', icon: CreditCard },
  { name: 'Import', href: '/import', icon: Upload },
  { name: 'Recurring', href: '/recurring', icon: Repeat },
  { name: 'Transfers', href: '/transfers', icon: ArrowRightLeft },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Sidebar({ className }: { className?: string }) {
  const pathname = usePathname()

  // Check if current path matches nav item (including sub-routes for settings)
  const isActive = (href: string) => {
    if (href === '/') return pathname === '/'
    if (href === '/settings') return pathname.startsWith('/settings')
    return pathname === href
  }

  return (
    <div className={cn("pb-12 h-screen border-r bg-background w-64 hidden md:block fixed left-0 top-0", className)}>
      <div className="space-y-4 py-4">
        <div className="px-3 py-2">
          <h2 className="mb-2 px-4 text-lg font-semibold tracking-tight">
            LedgerLoop
          </h2>
          <div className="space-y-1">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center rounded-md px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors",
                  isActive(item.href) ? "bg-accent text-accent-foreground" : "text-muted-foreground"
                )}
              >
                <item.icon className="mr-2 h-4 w-4" />
                {item.name}
              </Link>
            ))}
          </div>
        </div>
        <div className="px-3 py-2">
           <button 
             className="w-full flex items-center rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm hover:bg-accent hover:text-accent-foreground"
             onClick={() => document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }))}
           >
             <Search className="mr-2 h-4 w-4 text-muted-foreground" />
             <span className="text-muted-foreground">Search...</span>
             <kbd className="pointer-events-none ml-auto inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground opacity-100">
               <span className="text-xs">⌘</span>K
             </kbd>
           </button>
        </div>
      </div>
    </div>
  )
}
