"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Settings, Tags, Zap, Activity, Database } from "lucide-react"

const settingsNav = [
  { name: "General", href: "/settings", icon: Settings },
  { name: "Categories", href: "/settings/categories", icon: Tags },
  { name: "Automation", href: "/settings/automation", icon: Zap },
  { name: "System", href: "/settings/system", icon: Activity },
]

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your preferences, categories, automation rules, and system configuration.
        </p>
      </div>

      {/* Sub-navigation */}
      <div className="flex gap-1 border-b">
        {settingsNav.map((item) => {
          const isActive = pathname === item.href ||
            (item.href !== "/settings" && pathname.startsWith(item.href))

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
                isActive
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/50"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.name}
            </Link>
          )
        })}
      </div>

      {/* Content */}
      <div>{children}</div>
    </div>
  )
}
