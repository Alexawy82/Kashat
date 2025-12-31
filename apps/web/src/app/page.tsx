'use client'

import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Upload } from 'lucide-react'

// Hero Components
import { HeroNetWorth, HeroThisMonth, HeroHealthScore } from '@/components/dashboard/hero'

// Card Components
import {
  SmartInsightsCard,
  UpcomingBillsCard,
  SpendingByCategoryCard,
  RecentTransactionsCard,
  SuggestionsCard,
  BudgetSummaryCard,
  IncomeCard,
} from '@/components/dashboard/cards'

// Hooks
import { useCompleteNetWorth } from '@/hooks/useNetWorth'
import { useAnalyticsDashboard } from '@/hooks/useAnalytics'
import { useFinancialHealth } from '@/hooks/useIntelligence'

export default function DashboardPage() {
  // Fetch data for hero section
  const { data: netWorthData, isLoading: netWorthLoading } = useCompleteNetWorth()
  const { data: analyticsData, isLoading: analyticsLoading } = useAnalyticsDashboard()
  const { data: healthData, isLoading: healthLoading } = useFinancialHealth()

  // Extract values from analytics
  const income = analyticsData?.summary?.income ?? 0
  const spending = analyticsData?.summary?.spending ?? 0
  const saved = income - spending
  const savingsRate = income > 0 ? (saved / income) * 100 : 0

  // Extract health data
  const healthReport = healthData?.health_report
  const healthScore = healthReport?.overall_score ?? 0
  const healthGrade = healthReport?.health_grade ?? 'C'
  const healthComponents = healthReport?.component_scores
  const healthStrengths = healthReport?.key_strengths ?? []
  const healthImprovements = healthReport?.improvement_areas ?? []
  const healthRecommendations = healthReport?.recommendations ?? []

  // Build net worth breakdown for modal
  const netWorthBreakdown = netWorthData
    ? {
        assets: [
          {
            type: 'checking',
            label: 'Checking',
            total: netWorthData.bank_accounts ?? 0,
            items:
              netWorthData.assets
                ?.filter((a: any) => a.asset_type === 'checking')
                .map((a: any) => ({
                  id: a.id,
                  name: a.name,
                  value: a.current_value,
                })) || [],
          },
          {
            type: 'investment',
            label: 'Investments',
            total: netWorthData.asset_breakdown?.investment ?? 0,
            items:
              netWorthData.assets
                ?.filter((a: any) => a.asset_type === 'investment')
                .map((a: any) => ({
                  id: a.id,
                  name: a.name,
                  value: a.current_value,
                })) || [],
          },
          {
            type: 'real_estate',
            label: 'Real Estate',
            total: netWorthData.asset_breakdown?.real_estate ?? 0,
            items:
              netWorthData.assets
                ?.filter((a: any) => a.asset_type === 'real_estate')
                .map((a: any) => ({
                  id: a.id,
                  name: a.name,
                  value: a.current_value,
                })) || [],
          },
          {
            type: 'vehicle',
            label: 'Vehicles',
            total: netWorthData.asset_breakdown?.vehicle ?? 0,
            items:
              netWorthData.assets
                ?.filter((a: any) => a.asset_type === 'vehicle')
                .map((a: any) => ({
                  id: a.id,
                  name: a.name,
                  value: a.current_value,
                })) || [],
          },
        ].filter((g) => g.total > 0 || g.items.length > 0),
        liabilities: [
          {
            type: 'mortgage',
            label: 'Mortgage',
            total: netWorthData.liability_breakdown?.mortgage ?? 0,
            items:
              netWorthData.liabilities
                ?.filter((l: any) => l.liability_type === 'mortgage')
                .map((l: any) => ({
                  id: l.id,
                  name: l.name,
                  value: l.current_balance,
                })) || [],
          },
          {
            type: 'auto_loan',
            label: 'Auto Loans',
            total: netWorthData.liability_breakdown?.auto_loan ?? 0,
            items:
              netWorthData.liabilities
                ?.filter((l: any) => l.liability_type === 'auto_loan')
                .map((l: any) => ({
                  id: l.id,
                  name: l.name,
                  value: l.current_balance,
                })) || [],
          },
          {
            type: 'credit_card',
            label: 'Credit Cards',
            total: netWorthData.liability_breakdown?.credit_card ?? 0,
            items:
              netWorthData.liabilities
                ?.filter((l: any) => l.liability_type === 'credit_card')
                .map((l: any) => ({
                  id: l.id,
                  name: l.name,
                  value: l.current_balance,
                })) || [],
          },
        ].filter((g) => g.total > 0 || g.items.length > 0),
        netWorth: netWorthData.net_worth ?? 0,
      }
    : undefined

  return (
    <div className="container mx-auto p-4 md:p-6 space-y-6 max-w-6xl">
      {/* Header */}
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Your financial overview at a glance</p>
        </div>
        <Link href="/import">
          <Button>
            <Upload className="h-4 w-4 mr-2" />
            Import Data
          </Button>
        </Link>
      </header>

      {/* SECTION 1: HERO - Key Metrics */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <HeroNetWorth
          netWorth={netWorthData?.net_worth ?? 0}
          change={0}
          changePercent={0}
          breakdown={netWorthBreakdown}
          isLoading={netWorthLoading}
        />
        <HeroThisMonth
          income={income}
          spending={spending}
          saved={saved}
          savingsRate={savingsRate}
          isLoading={analyticsLoading}
        />
        <HeroHealthScore
          score={healthScore}
          grade={healthGrade}
          components={healthComponents}
          strengths={healthStrengths}
          improvements={healthImprovements}
          recommendations={healthRecommendations}
          isLoading={healthLoading}
        />
      </section>

      {/* SECTION 2: SUGGESTIONS - Net Worth Intelligence (shows only when there are suggestions) */}
      <SuggestionsCard />

      {/* SECTION 3: ACTIONS - What Needs Attention */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SmartInsightsCard />
        <BudgetSummaryCard />
        <UpcomingBillsCard />
      </section>

      {/* SECTION 4: GLANCE - Quick Reference */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <IncomeCard />
        <SpendingByCategoryCard />
        <RecentTransactionsCard />
      </section>
    </div>
  )
}
