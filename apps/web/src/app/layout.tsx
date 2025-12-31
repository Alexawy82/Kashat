import './globals.css'
import { Providers } from '@/components/providers'
import { cn } from '@/lib/utils'
import { Sidebar } from '@/components/layout/Sidebar'
import { MobileNav } from '@/components/layout/MobileNav'
import { BottomNav } from '@/components/layout/BottomNav'
import { CommandPalette } from '@/components/layout/CommandPalette'
import { Toaster } from '@/components/ui/Toaster'
import { ErrorBoundary } from '@/components/ui/ErrorBoundary'

export const metadata = {
  title: 'Kashat',
  description: 'Your money, your data, your rules.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={cn(
          "min-h-screen bg-background font-sans antialiased",
        )}>
        <Providers>
          {/* Skip to main content link for accessibility */}
          <a
            href="#main-content"
            className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-1/2 focus:-translate-x-1/2 focus:z-[100] focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:shadow-lg"
          >
            Skip to main content
          </a>

          {/* Mobile Navigation */}
          <MobileNav />

          <div className="flex h-screen overflow-hidden">
            {/* Desktop Sidebar - hidden on mobile */}
            <Sidebar className="hidden md:block" />

            {/* Main Content */}
            <main
              id="main-content"
              className="flex-1 md:ml-64 overflow-y-auto bg-slate-50 dark:bg-background pt-16 md:pt-0 pb-20 md:pb-0 p-4 md:p-8"
            >
              <ErrorBoundary>
                {children}
              </ErrorBoundary>
            </main>
          </div>

          {/* Mobile Bottom Navigation */}
          <BottomNav />

          {/* Command Palette */}
          <CommandPalette />

          {/* Toast Notifications */}
          <Toaster />
        </Providers>
      </body>
    </html>
  )
}
