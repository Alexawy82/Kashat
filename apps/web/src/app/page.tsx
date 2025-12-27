'use client'

import Link from 'next/link'
import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Upload, LayoutGrid, TrendingUp, TrendingDown, BarChart3,
  DollarSign, PiggyBank, Loader2, AlertTriangle, LineChart, Sparkles
} from 'lucide-react'

// Dashboard components
import { HealthScoreCard } from '@/components/dashboard/HealthScoreCard'
import { RunwayCard } from '@/components/dashboard/RunwayCard'
import { IntelligenceFeed } from '@/components/dashboard/IntelligenceFeed'
import { SpendingBehaviorCard } from '@/components/dashboard/SpendingBehaviorCard'
import { CashflowSummaryCard } from '@/components/dashboard/CashflowSummaryCard'
import { AnomalyAlerts } from '@/components/dashboard/AnomalyAlerts'
import { RecurringSummaryWidget } from '@/components/dashboard/RecurringSummaryWidget'

// Analytics hooks
import {
  useAnalyticsDashboard,
  useAnalyticsMerchants,
  useSpendingPatterns,
  useAITrends,
  useSpendingForecast,
  useRecurringAnalytics,
  useIncomeForecast,
  useCashflowForecast,
  usePredictivePatterns
} from '@/hooks/useAnalytics'
import { useSpendingByType } from '@/hooks/useRecurring'

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState('overview')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">Your AI-powered financial command center.</p>
        </div>
        <Link href="/import">
          <Button variant="outline">
            <Upload className="mr-2 h-4 w-4" />
            Import Data
          </Button>
        </Link>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full max-w-lg grid-cols-4">
          <TabsTrigger value="overview" className="gap-2">
            <LayoutGrid className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="spending" className="gap-2">
            <BarChart3 className="h-4 w-4" />
            Spending
          </TabsTrigger>
          <TabsTrigger value="trends" className="gap-2">
            <Sparkles className="h-4 w-4" />
            Trends
          </TabsTrigger>
          <TabsTrigger value="forecast" className="gap-2">
            <LineChart className="h-4 w-4" />
            Forecast
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <OverviewTab />
        </TabsContent>

        {/* Spending Tab */}
        <TabsContent value="spending" className="space-y-6">
          <SpendingTab />
        </TabsContent>

        {/* Trends Tab */}
        <TabsContent value="trends" className="space-y-6">
          <TrendsTab />
        </TabsContent>

        {/* Forecast Tab */}
        <TabsContent value="forecast" className="space-y-6">
          <ForecastTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}

// ===== OVERVIEW TAB =====
function OverviewTab() {
  return (
    <>
      {/* Stats Grid - Top Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <HealthScoreCard />
        <RunwayCard />
        <CashflowSummaryCard />
        <SpendingBehaviorCard />
      </div>

      {/* Main Content Area */}
      <div className="grid gap-4 lg:grid-cols-7">
        {/* Intelligence Feed - Left Side */}
        <IntelligenceFeed />

        {/* Right Side - Anomalies & Quick Actions */}
        <div className="col-span-4 space-y-4">
          <AnomalyAlerts />
          <RecurringSummaryWidget />

          {/* Quick Actions */}
          <div className="grid gap-4 md:grid-cols-2">
            <Link href="/transactions?uncategorized=true" className="block">
              <div className="rounded-xl border bg-card text-card-foreground shadow p-6 hover:bg-accent/50 transition-colors cursor-pointer">
                <h3 className="font-semibold text-sm">Uncategorized Transactions</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Review and categorize transactions without categories
                </p>
              </div>
            </Link>
            <Link href="/recurring" className="block">
              <div className="rounded-xl border bg-card text-card-foreground shadow p-6 hover:bg-accent/50 transition-colors cursor-pointer">
                <h3 className="font-semibold text-sm">Recurring Detection</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Review detected subscriptions and recurring charges
                </p>
              </div>
            </Link>
            <Link href="/transfers" className="block">
              <div className="rounded-xl border bg-card text-card-foreground shadow p-6 hover:bg-accent/50 transition-colors cursor-pointer">
                <h3 className="font-semibold text-sm">People & Transfers</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  View counterparties and match internal transfers
                </p>
              </div>
            </Link>
            <Link href="/settings/automation" className="block">
              <div className="rounded-xl border bg-card text-card-foreground shadow p-6 hover:bg-accent/50 transition-colors cursor-pointer">
                <h3 className="font-semibold text-sm">Automation Rules</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Create rules to auto-categorize transactions
                </p>
              </div>
            </Link>
          </div>
        </div>
      </div>
    </>
  )
}

// ===== SPENDING TAB =====
function SpendingTab() {
  const { data: dashboardData, isLoading: dashboardLoading } = useAnalyticsDashboard({ include_ai: true })
  const { data: merchantsData, isLoading: merchantsLoading } = useAnalyticsMerchants({ limit: 10 })
  const { data: recurringData, isLoading: recurringLoading } = useRecurringAnalytics()
  const { data: recurringByType } = useSpendingByType()

  const dashboard = dashboardData || {}
  const current = dashboard.current_period || {}
  const previous = dashboard.previous_period || {}
  const merchants = merchantsData || []

  const spendChange = previous.spend
    ? ((current.spend - previous.spend) / Math.abs(previous.spend) * 100)
    : 0

  const incomeChange = previous.income
    ? ((current.income - previous.income) / Math.abs(previous.income) * 100)
    : 0

  return (
    <>
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Income</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {dashboardLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div className="text-2xl font-bold text-green-600">
                  ${(current.income || 0).toLocaleString()}
                </div>
                <p className={`text-xs flex items-center gap-1 ${incomeChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {incomeChange >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                  {Math.abs(incomeChange).toFixed(1)}% from last period
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Spending</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {dashboardLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div className="text-2xl font-bold text-red-600">
                  ${Math.abs(current.spend || 0).toLocaleString()}
                </div>
                <p className={`text-xs flex items-center gap-1 ${spendChange <= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {spendChange <= 0 ? <TrendingDown className="h-3 w-3" /> : <TrendingUp className="h-3 w-3" />}
                  {Math.abs(spendChange).toFixed(1)}% from last period
                </p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Net Cashflow</CardTitle>
            <PiggyBank className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {dashboardLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                <div className={`text-2xl font-bold ${(current.net || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {(current.net || 0) >= 0 ? '+' : ''}${(current.net || 0).toLocaleString()}
                </div>
                <p className="text-xs text-muted-foreground">This period</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Savings Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {dashboardLoading ? (
              <div className="h-8 bg-muted animate-pulse rounded" />
            ) : (
              <>
                {(() => {
                  const rate = current.income > 0
                    ? ((current.income - Math.abs(current.spend)) / current.income * 100)
                    : 0
                  return (
                    <>
                      <div className={`text-2xl font-bold ${rate >= 20 ? 'text-green-600' : rate >= 10 ? 'text-yellow-600' : 'text-red-600'}`}>
                        {rate.toFixed(1)}%
                      </div>
                      <p className="text-xs text-muted-foreground">Target: 20%</p>
                    </>
                  )
                })()}
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Top Merchants */}
        <Card>
          <CardHeader>
            <CardTitle>Top Merchants</CardTitle>
            <CardDescription>Where your money goes</CardDescription>
          </CardHeader>
          <CardContent>
            {merchantsLoading ? (
              <div className="flex justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : merchants.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center p-4">No merchant data available</p>
            ) : (
              <div className="space-y-3">
                {merchants.slice(0, 10).map((merchant: any, i: number) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-muted-foreground w-6">{i + 1}.</span>
                      <span className="text-sm font-medium truncate max-w-[200px]">
                        {merchant.merchant || merchant.name}
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-sm font-semibold">${Math.abs(merchant.spend || merchant.total || 0).toLocaleString()}</span>
                      <span className="text-xs text-muted-foreground ml-2">({merchant.count || 0} txns)</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recurring Expenses */}
        <Card>
          <CardHeader>
            <CardTitle>Recurring Expenses</CardTitle>
            <CardDescription>Monthly subscriptions and regular payments</CardDescription>
          </CardHeader>
          <CardContent>
            {recurringLoading ? (
              <div className="flex justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : !recurringData ? (
              <p className="text-sm text-muted-foreground text-center p-4">No recurring expenses detected</p>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-100">
                  <span className="text-sm font-medium">Total Monthly</span>
                  <span className="text-lg font-bold text-blue-700">
                    ${(recurringData.total_monthly_recurring || 0).toLocaleString()}
                  </span>
                </div>
                {recurringData.categories?.slice(0, 4).map((cat: any, i: number) => (
                  <div key={i} className="flex items-center justify-between">
                    <span className="text-sm">{cat.name}</span>
                    <div className="text-right">
                      <span className="text-sm font-medium">${(cat.amount || 0).toLocaleString()}</span>
                      <span className="text-xs text-muted-foreground ml-2">({cat.count} items)</span>
                    </div>
                  </div>
                ))}
                {recurringByType?.by_type?.length > 0 && (
                  <div className="pt-3 border-t">
                    <div className="text-xs text-muted-foreground mb-2">By type</div>
                    <div className="space-y-2">
                      {recurringByType.by_type.slice(0, 3).map((row: any) => (
                        <div key={row.type} className="flex items-center justify-between text-sm">
                          <span className="capitalize">{row.type.replace('_', ' ')}</span>
                          <span className="font-medium">${(row.monthly_total || 0).toLocaleString()}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  )
}

// ===== TRENDS TAB =====
function TrendsTab() {
  const { data: patternsData, isLoading: patternsLoading } = useSpendingPatterns()
  const { data: trendsData, isLoading: trendsLoading } = useAITrends()
  const { data: predictiveData, isLoading: predictiveLoading } = usePredictivePatterns()

  const patterns = patternsData?.patterns || []
  const trends = trendsData?.trends || []

  return (
    <>
      <div className="grid gap-6 lg:grid-cols-2">
        {/* AI Spending Patterns */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Spending Patterns
              <Badge variant="secondary">AI</Badge>
            </CardTitle>
            <CardDescription>AI-detected spending behaviors</CardDescription>
          </CardHeader>
          <CardContent>
            {patternsLoading ? (
              <div className="flex justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : patterns.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center p-4">No patterns detected yet</p>
            ) : (
              <div className="space-y-3">
                {patterns.slice(0, 6).map((pattern: any, i: number) => (
                  <div key={i} className="p-3 bg-muted/50 rounded-lg">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">{pattern.category}</span>
                      <Badge variant="outline" className="text-xs">
                        {(pattern.confidence * 100).toFixed(0)}% confident
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {pattern.pattern_type}: {pattern.frequency}
                      {pattern.seasonality && ` (${pattern.seasonality})`}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* AI Trends */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Trend Analysis
              <Badge variant="secondary">AI</Badge>
            </CardTitle>
            <CardDescription>Significant changes in your finances</CardDescription>
          </CardHeader>
          <CardContent>
            {trendsLoading ? (
              <div className="flex justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : trends.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center p-4">No significant trends detected</p>
            ) : (
              <div className="space-y-3">
                {trends.filter((t: any) => t.is_significant).slice(0, 6).map((trend: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-2 border rounded-lg">
                    <div className="flex items-center gap-2">
                      {trend.trend_direction === 'up' || trend.change_percentage > 0 ? (
                        <TrendingUp className="h-4 w-4 text-green-500" />
                      ) : (
                        <TrendingDown className="h-4 w-4 text-red-500" />
                      )}
                      <span className="text-sm font-medium">{trend.metric_name}</span>
                    </div>
                    <Badge className={trend.change_percentage > 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                      {trend.change_percentage > 0 ? '+' : ''}{trend.change_percentage?.toFixed(1)}%
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Predictive Patterns */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Predictive Patterns
              <Badge variant="secondary">AI</Badge>
            </CardTitle>
            <CardDescription>AI-detected behavioral patterns and anomaly likelihood</CardDescription>
          </CardHeader>
          <CardContent>
            {predictiveLoading ? (
              <div className="flex justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : !predictiveData ? (
              <p className="text-sm text-muted-foreground text-center p-4">Building pattern analysis...</p>
            ) : (
              <div className="grid gap-6 md:grid-cols-3">
                {/* Anomaly Likelihood */}
                {predictiveData.anomaly_likelihood !== undefined && (
                  <div className="flex flex-col items-center justify-center p-4 bg-muted/50 rounded-lg">
                    <span className="text-xs text-muted-foreground mb-1">Anomaly Likelihood</span>
                    <span className={`text-3xl font-bold ${
                      predictiveData.anomaly_likelihood < 0.3 ? 'text-green-600' :
                      predictiveData.anomaly_likelihood < 0.6 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {(predictiveData.anomaly_likelihood * 100).toFixed(0)}%
                    </span>
                  </div>
                )}

                {/* Spending Patterns */}
                <div className="space-y-3">
                  <h4 className="text-sm font-medium">Spending Patterns</h4>
                  {predictiveData.spending_patterns?.slice(0, 4).map((pattern: any, i: number) => (
                    <div key={i} className="flex items-center justify-between text-sm">
                      <span className="truncate max-w-[120px]">{pattern.category}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-muted-foreground">${(pattern.avg_amount || 0).toLocaleString()}</span>
                        {pattern.trend && (
                          pattern.trend === 'up' ?
                            <TrendingUp className="h-3 w-3 text-red-500" /> :
                            <TrendingDown className="h-3 w-3 text-green-500" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Income Patterns */}
                <div className="space-y-3">
                  <h4 className="text-sm font-medium">Income Patterns</h4>
                  {predictiveData.income_patterns?.length > 0 ? (
                    predictiveData.income_patterns.slice(0, 4).map((pattern: any, i: number) => (
                      <div key={i} className="flex items-center justify-between text-sm">
                        <span className="truncate max-w-[120px]">{pattern.source}</span>
                        <span className="text-green-600">${(pattern.avg_amount || 0).toLocaleString()}</span>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-muted-foreground">No income patterns detected</p>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  )
}

// ===== FORECAST TAB =====
function ForecastTab() {
  const { data: forecastData, isLoading: forecastLoading } = useSpendingForecast({ forecast_months: 3 })
  const { data: incomeData, isLoading: incomeLoading } = useIncomeForecast({ forecast_months: 3 })
  const { data: cashflowData, isLoading: cashflowLoading } = useCashflowForecast({ months: 6 })

  const forecast = forecastData || {}

  return (
    <>
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Spending Forecast */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Spending Forecast
              <Badge variant="secondary">AI</Badge>
            </CardTitle>
            <CardDescription>Predicted spending for next 3 months</CardDescription>
          </CardHeader>
          <CardContent>
            {forecastLoading ? (
              <div className="flex justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : !forecast.forecast_points ? (
              <p className="text-sm text-muted-foreground text-center p-4">Insufficient data for forecasting</p>
            ) : (
              <div className="space-y-4">
                {forecast.forecast_points?.slice(0, 3).map((point: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
                    <span className="text-sm font-medium">{point.month || point.period}</span>
                    <div className="text-right">
                      <span className="text-sm font-semibold">${Math.abs(point.predicted_value || point.value || 0).toLocaleString()}</span>
                      {point.confidence_low && point.confidence_high && (
                        <p className="text-xs text-muted-foreground">
                          Range: ${point.confidence_low.toLocaleString()} - ${point.confidence_high.toLocaleString()}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Income Forecast */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Income Forecast
              <Badge variant="secondary">AI</Badge>
            </CardTitle>
            <CardDescription>Predicted income for upcoming months</CardDescription>
          </CardHeader>
          <CardContent>
            {incomeLoading ? (
              <div className="flex justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : !incomeData ? (
              <p className="text-sm text-muted-foreground text-center p-4">Insufficient income data for forecasting</p>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-green-50 rounded-lg border border-green-100">
                    <p className="text-xs text-muted-foreground">Current Monthly</p>
                    <p className="text-lg font-bold text-green-700">
                      ${(incomeData.current_monthly_income || 0).toLocaleString()}
                    </p>
                  </div>
                  <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
                    <p className="text-xs text-muted-foreground">Predicted</p>
                    <p className="text-lg font-bold text-blue-700">
                      ${(incomeData.predicted_monthly_income || 0).toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Trend</span>
                  <Badge variant={incomeData.trend === 'up' ? 'default' : incomeData.trend === 'down' ? 'destructive' : 'secondary'}>
                    {incomeData.trend || 'stable'}
                  </Badge>
                </div>
                {incomeData.confidence && (
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Confidence</span>
                    <span className="font-medium">{(incomeData.confidence * 100).toFixed(0)}%</span>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Cashflow Projection - Full Width */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Cashflow Projection
              <Badge variant="secondary">AI</Badge>
            </CardTitle>
            <CardDescription>6-month financial projection with monthly breakdown</CardDescription>
          </CardHeader>
          <CardContent>
            {cashflowLoading ? (
              <div className="flex justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : !cashflowData ? (
              <p className="text-sm text-muted-foreground text-center p-4">Insufficient data for cashflow projection</p>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <div className="p-3 bg-muted/50 rounded-lg">
                    <p className="text-xs text-muted-foreground">Current Balance</p>
                    <p className={`text-lg font-bold ${(cashflowData.current_balance || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      ${(cashflowData.current_balance || 0).toLocaleString()}
                    </p>
                  </div>
                  <div className="p-3 bg-muted/50 rounded-lg">
                    <p className="text-xs text-muted-foreground">Projected (6mo)</p>
                    <p className={`text-lg font-bold ${(cashflowData.projected_balance || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      ${(cashflowData.projected_balance || 0).toLocaleString()}
                    </p>
                  </div>
                  {cashflowData.risk_level && (
                    <div className="p-3 bg-muted/50 rounded-lg flex items-center gap-2">
                      <AlertTriangle className={`h-5 w-5 ${
                        cashflowData.risk_level === 'low' ? 'text-green-500' :
                        cashflowData.risk_level === 'medium' ? 'text-yellow-500' : 'text-red-500'
                      }`} />
                      <div>
                        <p className="text-xs text-muted-foreground">Risk Level</p>
                        <p className="text-sm font-medium capitalize">{cashflowData.risk_level}</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Monthly breakdown table */}
                {cashflowData.monthly_projections?.length > 0 && (
                  <div className="border rounded-lg overflow-hidden">
                    <div className="grid grid-cols-4 gap-4 p-3 bg-muted/50 text-sm font-medium">
                      <span>Month</span>
                      <span className="text-right">Income</span>
                      <span className="text-right">Expenses</span>
                      <span className="text-right">Balance</span>
                    </div>
                    {cashflowData.monthly_projections.slice(0, 6).map((proj: any, i: number) => (
                      <div key={i} className="grid grid-cols-4 gap-4 p-3 border-t text-sm">
                        <span className="text-muted-foreground">{proj.month}</span>
                        <span className="text-right text-green-600">+${(proj.income || 0).toLocaleString()}</span>
                        <span className="text-right text-red-600">-${Math.abs(proj.expenses || 0).toLocaleString()}</span>
                        <span className={`text-right font-medium ${(proj.balance || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          ${(proj.balance || 0).toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  )
}
