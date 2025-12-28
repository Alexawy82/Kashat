import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { TypeSection } from '@/app/subscriptions/components/TypeSection'
import { RecurringSeries, sumMonthly, formatAmount } from '@/app/subscriptions/lib/recurringUtils'
import {
  CreditCard,
  Home,
  Landmark,
  Shield,
  Tv,
  Layers,
} from 'lucide-react'

export type TypeTab = {
  key: string
  label: string
  title: string
  description?: string
  items: RecurringSeries[]
  isLoading?: boolean
  onSelect?: (item: RecurringSeries) => void
}

const tabIcons: Record<string, typeof Tv> = {
  all: Layers,
  subscriptions: Tv,
  bills: Home,
  loans: Landmark,
  'credit-cards': CreditCard,
  insurance: Shield,
}

const tabColors: Record<string, string> = {
  all: 'text-primary',
  subscriptions: 'text-purple-600',
  bills: 'text-blue-600',
  loans: 'text-amber-600',
  'credit-cards': 'text-green-600',
  insurance: 'text-red-600',
}

export function TypeTabs({
  tabs,
  value,
  onValueChange,
}: {
  tabs: TypeTab[]
  value?: string
  onValueChange?: (next: string) => void
}) {
  const defaultTab = tabs[0]?.key || 'all'

  return (
    <Tabs value={value} defaultValue={defaultTab} onValueChange={onValueChange} className="space-y-4">
      <TabsList className="flex flex-wrap h-auto gap-1 p-1 bg-muted/50">
        {tabs.map((tab) => {
          const Icon = tabIcons[tab.key] || Layers
          const colorClass = tabColors[tab.key] || 'text-primary'
          const monthlyTotal = sumMonthly(tab.items)

          return (
            <TabsTrigger
              key={tab.key}
              value={tab.key}
              className="flex items-center gap-2 px-3 py-2 data-[state=active]:bg-background"
            >
              <Icon className={`h-4 w-4 ${value === tab.key ? colorClass : 'text-muted-foreground'}`} />
              <span>{tab.label}</span>
              {tab.items.length > 0 && (
                <Badge
                  variant={value === tab.key ? 'default' : 'secondary'}
                  className="text-[10px] px-1.5 py-0 h-4 min-w-[1.25rem]"
                >
                  {tab.items.length}
                </Badge>
              )}
            </TabsTrigger>
          )
        })}
      </TabsList>
      {tabs.map((tab) => (
        <TabsContent key={tab.key} value={tab.key} className="mt-4">
          <TypeSection
            title={tab.title}
            description={tab.description}
            items={tab.items}
            isLoading={tab.isLoading}
            onSelect={tab.onSelect}
            tabKey={tab.key}
          />
        </TabsContent>
      ))}
    </Tabs>
  )
}
