'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { useAppData } from '../../contexts/AppDataContext'
import { sharedAnalytics } from '../../services/SharedAnalyticsService'
import type { ConsolidatedMetrics, CrossFeatureInsights } from '../../services/SharedAnalyticsService'
import { useAnalyticsSummary } from '../../hooks/useAnalyticsSummary'
import { useAnalyticsPredictions } from '../../hooks/useAnalyticsPredictions'
import { UI_V1_COMPLETE } from '../../utils/config'

interface EnhancedDashboardProps {
  timeRange?: string
  enableRealTime?: boolean
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

function formatMonth(month: string) {
  return new Date(month).toLocaleDateString('en-US', { year: 'numeric', month: 'short' })
}

function formatPercentage(value: number) {
  return `${value.toFixed(1)}%`
}

function getChangeIcon(change: number) {
  if (change > 0) return '↗️'
  if (change < 0) return '↘️'
  return '➡️'
}

function getChangeColor(change: number) {
  if (change > 0) return '#dc2626'
  if (change < 0) return '#059669'
  return '#6b7280'
}

function SimpleChart({ data, width = 300, height = 120, dataKey = 'amount' }: any) {
  if (!data || data.length === 0) return null
  
  const values = data.map((d: any) => Math.abs(d[dataKey] || 0))
  const max = Math.max(1, ...values)
  const pad = 8
  const barWidth = Math.max(4, (width - 2*pad) / data.length - 2)
  
  return (
    <svg width={width} height={height} style={{ background: '#f9f9f9', borderRadius: 4 }}>
      {data.map((d: any, i: number) => {
        const barHeight = ((d[dataKey] || 0) / max) * (height - 2*pad)
        const x = pad + i * (barWidth + 2)
        const y = height - pad - barHeight
        return (
          <rect key={i} x={x} y={y} width={barWidth} height={barHeight} fill="#3b82f6" />
        )
      })}
    </svg>
  )
}

function MetricCard({ 
  title, 
  value, 
  change, 
  format = 'number',
  description,
  trend,
  color = '#3b82f6'
}: {
  title: string
  value: number
  change?: number
  format?: 'currency' | 'number' | 'percentage'
  description?: string
  trend?: 'up' | 'down' | 'stable'
  color?: string
}) {
  const formatValue = (val: number) => {
    switch (format) {
      case 'currency': return formatCurrency(val)
      case 'percentage': return formatPercentage(val)
      default: return val.toLocaleString()
    }
  }

  return (
    <div style={{ 
      background: '#fff', 
      padding: 20, 
      borderRadius: 8, 
      border: '1px solid #e5e7eb',
      position: 'relative',
      overflow: 'hidden'
    }}>
      <div style={{ position: 'absolute', top: 0, left: 0, width: 4, height: '100%', background: color }} />
      
      <div style={{ fontSize: 14, color: '#6b7280', marginBottom: 8 }}>{title}</div>
      
      <div style={{ display: 'flex', alignItems: 'baseline', marginBottom: 8 }}>
        <div style={{ fontSize: 28, fontWeight: 600, color: '#111827' }}>
          {formatValue(value)}
        </div>
        
        {change !== undefined && (
          <div style={{ 
            marginLeft: 12, 
            fontSize: 14, 
            color: getChangeColor(change),
            display: 'flex',
            alignItems: 'center',
            gap: 4
          }}>
            <span>{getChangeIcon(change)}</span>
            <span>{change > 0 ? '+' : ''}{formatPercentage(change)}</span>
          </div>
        )}
      </div>

      {description && (
        <div style={{ fontSize: 12, color: '#9ca3af' }}>{description}</div>
      )}

      {trend && (
        <div style={{ 
          position: 'absolute', 
          top: 16, 
          right: 16,
          fontSize: 20
        }}>
          {trend === 'up' ? '📈' : trend === 'down' ? '📉' : '📊'}
        </div>
      )}
    </div>
  )
}

function AIInsightsPanel({ insights }: { insights: CrossFeatureInsights | null }) {
  if (!insights) return null

  const { transactionInsights, aiPerformance } = insights

  return (
    <div style={{ background: '#fff', padding: 20, borderRadius: 8, border: '1px solid #e5e7eb' }}>
      <h3 style={{ fontSize: 18, margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: 8 }}>
        🤖 AI System Performance
      </h3>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 12, marginBottom: 16 }}>
        <div style={{ textAlign: 'center', padding: 12, background: '#f0f9ff', borderRadius: 6 }}>
          <div style={{ fontSize: 20, fontWeight: 600, color: '#0369a1' }}>
            {transactionInsights.aiProcessedCount}
          </div>
          <div style={{ fontSize: 12, color: '#6b7280' }}>AI Processed</div>
        </div>
        
        <div style={{ textAlign: 'center', padding: 12, background: '#f0fdf4', borderRadius: 6 }}>
          <div style={{ fontSize: 20, fontWeight: 600, color: '#15803d' }}>
            {formatPercentage(aiPerformance.successRate)}
          </div>
          <div style={{ fontSize: 12, color: '#6b7280' }}>Success Rate</div>
        </div>
        
        <div style={{ textAlign: 'center', padding: 12, background: '#fffbeb', borderRadius: 6 }}>
          <div style={{ fontSize: 20, fontWeight: 600, color: '#d97706' }}>
            {Math.round(aiPerformance.averageLatency)}ms
          </div>
          <div style={{ fontSize: 12, color: '#6b7280' }}>Avg Latency</div>
        </div>

        <div style={{ textAlign: 'center', padding: 12, background: '#fef2f2', borderRadius: 6 }}>
          <div style={{ fontSize: 20, fontWeight: 600, color: '#dc2626' }}>
            {transactionInsights.anomalyCount}
          </div>
          <div style={{ fontSize: 12, color: '#6b7280' }}>Anomalies</div>
        </div>
      </div>

      {transactionInsights.uncategorizedCount > 0 && (
        <div style={{ 
          padding: 12, 
          background: '#fef3c7', 
          border: '1px solid #f59e0b', 
          borderRadius: 6,
          marginTop: 12
        }}>
          <div style={{ fontSize: 14, fontWeight: 500, color: '#92400e' }}>
            ⚠️ {transactionInsights.uncategorizedCount} transactions need categorization
          </div>
          <div style={{ fontSize: 12, color: '#78350f', marginTop: 4 }}>
            Consider running AI enhancement to auto-categorize
          </div>
        </div>
      )}
    </div>
  )
}

function RealTimeStatus({ realTime }: { realTime: any }) {
  return (
    <div style={{ 
      display: 'flex', 
      alignItems: 'center', 
      gap: 12,
      padding: '8px 12px',
      background: realTime.isConnected ? '#f0fdf4' : '#fef2f2',
      border: `1px solid ${realTime.isConnected ? '#bbf7d0' : '#fecaca'}`,
      borderRadius: 6
    }}>
      <div style={{ 
        width: 8, 
        height: 8, 
        borderRadius: '50%', 
        background: realTime.isConnected ? '#10b981' : '#ef4444',
        animation: realTime.isConnected ? 'pulse 2s infinite' : 'none'
      }} />
      
      <span style={{ 
        fontSize: 14, 
        color: realTime.isConnected ? '#15803d' : '#dc2626',
        fontWeight: 500
      }}>
        {realTime.isConnected ? 'Live Data' : 'Offline'}
      </span>
      
      {realTime.liveMetrics?.updated_at && (
        <span style={{ fontSize: 12, color: '#6b7280' }}>
          Updated: {new Date(realTime.liveMetrics.updated_at).toLocaleTimeString()}
        </span>
      )}
    </div>
  )
}

export default function EnhancedDashboard({ 
  timeRange = '90d', 
  enableRealTime = true 
}: EnhancedDashboardProps) {
  const { state, loadAnalytics } = useAppData()
  const { data: v1Summary } = useAnalyticsSummary({})
  const { data: v1Pred } = useAnalyticsPredictions({})
  const [consolidatedMetrics, setConsolidatedMetrics] = useState<ConsolidatedMetrics | null>(null)
  const [crossFeatureInsights, setCrossFeatureInsights] = useState<CrossFeatureInsights | null>(null)
  const [selectedTimeRange, setSelectedTimeRange] = useState(timeRange)
  const [loading, setLoading] = useState(false)

  // Load enhanced analytics data
  useEffect(() => {
    async function loadEnhancedData() {
      setLoading(true)
      try {
        const [metrics, insights] = await Promise.all([
          sharedAnalytics.getConsolidatedMetrics({ timeRange: selectedTimeRange }),
          sharedAnalytics.getCrossFeatureInsights()
        ])
        
        setConsolidatedMetrics(metrics)
        setCrossFeatureInsights(insights)
      } catch (error) {
        console.error('Failed to load enhanced analytics:', error)
      } finally {
        setLoading(false)
      }
    }

    loadEnhancedData()
  }, [selectedTimeRange])

  // Auto-refresh data every 2 minutes
  useEffect(() => {
    if (!enableRealTime) return

    const interval = setInterval(async () => {
      try {
        const [metrics, insights] = await Promise.all([
          sharedAnalytics.getConsolidatedMetrics({ timeRange: selectedTimeRange }),
          sharedAnalytics.getCrossFeatureInsights()
        ])
        
        setConsolidatedMetrics(metrics)
        setCrossFeatureInsights(insights)
      } catch (error) {
        console.error('Auto-refresh failed:', error)
      }
    }, 2 * 60 * 1000) // 2 minutes

    return () => clearInterval(interval)
  }, [selectedTimeRange, enableRealTime])

  const timeRangeOptions = [
    { value: '30d', label: '30 Days' },
    { value: '90d', label: '90 Days' },
    { value: '365d', label: '1 Year' }
  ]

  if (loading && !consolidatedMetrics) {
    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        height: 200,
        background: '#fff',
        borderRadius: 8,
        border: '1px solid #e5e7eb'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ 
            width: 32, 
            height: 32, 
            border: '3px solid #e5e7eb',
            borderTop: '3px solid #3b82f6',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 12px'
          }} />
          <div style={{ color: '#6b7280' }}>Loading enhanced analytics...</div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: 20 }}>
      {UI_V1_COMPLETE && (
        <div style={{
          marginBottom: 12,
          padding: '8px 12px',
          background: '#eef2ff',
          border: '1px solid #c7d2fe',
          borderRadius: 6,
          color: '#3730a3'
        }}>
          New analytics enabled — {v1Summary ? `${v1Summary.totals.income.toFixed(2)} income / ${v1Summary.totals.spend.toFixed(2)} spend` : 'loading…'}
        </div>
      )}
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: 24 
      }}>
        <div>
          <h1 style={{ fontSize: 32, margin: 0, color: '#111827' }}>
            📊 Financial Dashboard
          </h1>
          <p style={{ color: '#6b7280', margin: '4px 0 0 0' }}>
            Unified analytics across all your financial data
          </p>
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <RealTimeStatus realTime={state.realTime} />
          
          <select
            value={selectedTimeRange}
            onChange={(e) => setSelectedTimeRange(e.target.value)}
            style={{
              padding: '8px 12px',
              border: '1px solid #d1d5db',
              borderRadius: 6,
              background: '#fff',
              fontSize: 14
            }}
          >
            {timeRangeOptions.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '8px 12px',
              background: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: 6,
              fontSize: 14,
              cursor: 'pointer'
            }}
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Key Metrics Overview */}
      {consolidatedMetrics && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 32 }}>
          <MetricCard
            title="Total Transactions"
            value={consolidatedMetrics.overview.totalTransactions}
            description="All time transactions"
            color="#3b82f6"
          />
          
          <MetricCard
            title="Total Amount"
            value={consolidatedMetrics.overview.totalAmount}
            format="currency"
            change={consolidatedMetrics.overview.monthlyGrowth}
            description="Total transaction volume"
            color="#059669"
          />
          
          <MetricCard
            title="Categorized"
            value={consolidatedMetrics.overview.categorizedPercentage}
            format="percentage"
            description={`${Math.round(consolidatedMetrics.overview.totalTransactions * consolidatedMetrics.overview.categorizedPercentage / 100)} transactions`}
            color="#8b5cf6"
          />
          
          <MetricCard
            title="AI Processed"
            value={consolidatedMetrics.overview.aiProcessedPercentage}
            format="percentage"
            description="Enhanced with AI insights"
            color="#f59e0b"
          />
        </div>
      )}

      {/* AI Financial Health */}
      {state.analytics.aiSummary && (
        <div style={{ 
          background: 'linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)', 
          padding: 24, 
          borderRadius: 12, 
          border: '1px solid #bae6fd', 
          marginBottom: 32 
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <h2 style={{ fontSize: 20, color: '#0c4a6e', margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
              🧠 AI Financial Health Analysis
            </h2>
            <div style={{ 
              background: state.analytics.aiSummary.health_score >= 80 ? '#10b981' : 
                         state.analytics.aiSummary.health_score >= 60 ? '#f59e0b' : '#ef4444',
              color: 'white',
              padding: '8px 16px',
              borderRadius: 20,
              fontSize: 16,
              fontWeight: 600
            }}>
              {Math.round(state.analytics.aiSummary.health_score)}/100
            </div>
          </div>
          <p style={{ margin: 0, color: '#075985', fontSize: 16, lineHeight: 1.5 }}>
            {state.analytics.aiSummary.summary}
          </p>
        </div>
      )}

      {/* Charts Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 24, marginBottom: 32 }}>
        
        {/* Monthly Spending Trend */}
        <div style={{ background: '#fff', padding: 20, borderRadius: 8, border: '1px solid #e5e7eb' }}>
          <h3 style={{ fontSize: 18, margin: '0 0 16px 0' }}>💰 Monthly Spending Trend</h3>
          {consolidatedMetrics?.spending.monthlyTrend && (
            <>
              <SimpleChart 
                data={consolidatedMetrics.spending.monthlyTrend} 
                width={350} 
                height={140}
                dataKey="amount"
              />
              <div style={{ maxHeight: 200, overflowY: 'auto', marginTop: 12 }}>
                <table style={{ width: '100%', fontSize: 14 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #e5e7eb' }}>
                      <th style={{ textAlign: 'left', padding: '4px 0' }}>Month</th>
                      <th style={{ textAlign: 'right', padding: '4px 0' }}>Amount</th>
                      <th style={{ textAlign: 'right', padding: '4px 0' }}>Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {consolidatedMetrics.spending.monthlyTrend.map((item, i) => (
                      <tr key={i}>
                        <td style={{ padding: '4px 0' }}>{formatMonth(item.month)}</td>
                        <td style={{ textAlign: 'right', padding: '4px 0' }}>
                          {formatCurrency(item.amount)}
                        </td>
                        <td style={{ 
                          textAlign: 'right', 
                          padding: '4px 0',
                          color: getChangeColor(item.change)
                        }}>
                          {item.change > 0 ? '+' : ''}{formatPercentage(item.change)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        {/* Category Breakdown */}
        <div style={{ background: '#fff', padding: 20, borderRadius: 8, border: '1px solid #e5e7eb' }}>
          <h3 style={{ fontSize: 18, margin: '0 0 16px 0' }}>📂 Category Breakdown</h3>
          {consolidatedMetrics?.spending.categoryBreakdown && (
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {consolidatedMetrics.spending.categoryBreakdown.slice(0, 8).map((cat, i) => (
                <div key={i} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center', 
                  padding: '8px 0', 
                  borderBottom: i < 7 ? '1px solid #f3f4f6' : 'none' 
                }}>
                  <div>
                    <div style={{ fontWeight: 500 }}>{cat.category}</div>
                    <div style={{ fontSize: 12, color: '#6b7280' }}>
                      {cat.transactionCount} transactions • {formatPercentage(cat.percentage)}
                    </div>
                  </div>
                  <div style={{ fontWeight: 600, color: '#dc2626' }}>
                    {formatCurrency(cat.amount)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI Insights Panel */}
        <AIInsightsPanel insights={crossFeatureInsights} />

        {/* Top Merchants */}
        <div style={{ background: '#fff', padding: 20, borderRadius: 8, border: '1px solid #e5e7eb' }}>
          <h3 style={{ fontSize: 18, margin: '0 0 16px 0' }}>🏪 Top Merchants</h3>
          {consolidatedMetrics?.spending.merchantAnalysis && (
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {consolidatedMetrics.spending.merchantAnalysis.slice(0, 8).map((merchant, i) => (
                <div key={i} style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center', 
                  padding: '8px 0', 
                  borderBottom: i < 7 ? '1px solid #f3f4f6' : 'none' 
                }}>
                  <div>
                    <div style={{ fontWeight: 500 }}>{merchant.merchant}</div>
                    <div style={{ fontSize: 12, color: '#6b7280' }}>
                      {merchant.frequency} visits • {formatCurrency(merchant.avgTransaction)} avg
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 600, color: '#dc2626' }}>
                      {formatCurrency(merchant.totalSpent)}
                    </div>
                    <div style={{ fontSize: 12, color: '#6b7280' }}>
                      {merchant.trend === 'up' ? '📈' : merchant.trend === 'down' ? '📉' : '➡️'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* AI Trends and Patterns */}
      {state.analytics.trends && state.analytics.trends.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: 24, marginBottom: 32 }}>
          
          {/* AI Trends */}
          <div style={{ background: '#fff', padding: 20, borderRadius: 8, border: '1px solid #e5e7eb' }}>
            <h3 style={{ fontSize: 18, margin: '0 0 16px 0' }}>📈 AI Trend Analysis</h3>
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {state.analytics.trends.slice(0, 5).map((trend, i) => (
                <div key={i} style={{ 
                  padding: 12, 
                  marginBottom: 8, 
                  background: trend.trend_type === 'increasing' ? '#fef2f2' : 
                             trend.trend_type === 'decreasing' ? '#f0fdf4' : '#f8fafc',
                  border: `1px solid ${trend.trend_type === 'increasing' ? '#fecaca' : 
                                      trend.trend_type === 'decreasing' ? '#bbf7d0' : '#e2e8f0'}`,
                  borderRadius: 6 
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <div style={{ fontWeight: 500, fontSize: 14 }}>{trend.category}</div>
                    <div style={{ 
                      fontSize: 12, 
                      fontWeight: 600,
                      color: trend.trend_type === 'increasing' ? '#dc2626' : 
                             trend.trend_type === 'decreasing' ? '#059669' : '#6b7280'
                    }}>
                      {trend.trend_type === 'increasing' ? '↗' : 
                       trend.trend_type === 'decreasing' ? '↘' : '→'} 
                      {Math.round(trend.confidence * 100)}%
                    </div>
                  </div>
                  <div style={{ fontSize: 12, color: '#6b7280' }}>{trend.description}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Spending Patterns */}
          {state.analytics.patterns && state.analytics.patterns.length > 0 && (
            <div style={{ background: '#fff', padding: 20, borderRadius: 8, border: '1px solid #e5e7eb' }}>
              <h3 style={{ fontSize: 18, margin: '0 0 16px 0' }}>🔍 Spending Patterns</h3>
              <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                {state.analytics.patterns.slice(0, 6).map((pattern, i) => (
                  <div key={i} style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center', 
                    padding: '8px 0', 
                    borderBottom: i < 5 ? '1px solid #f3f4f6' : 'none' 
                  }}>
                    <div>
                      <div style={{ fontWeight: 500, fontSize: 14 }}>{pattern.category}</div>
                      <div style={{ fontSize: 12, color: '#6b7280' }}>
                        {pattern.pattern_type} • {pattern.frequency} • {Math.round(pattern.confidence * 100)}% confidence
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontWeight: 600, color: '#dc2626' }}>
                        {formatCurrency(pattern.average_amount)}
                      </div>
                      <div style={{ 
                        fontSize: 10, 
                        color: pattern.trend_direction === 'increasing' ? '#dc2626' : 
                               pattern.trend_direction === 'decreasing' ? '#059669' : '#6b7280'
                      }}>
                        {pattern.trend_direction === 'increasing' ? '↗' : 
                         pattern.trend_direction === 'decreasing' ? '↘' : '→'} 
                        {pattern.trend_direction}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Predictions and Savings Opportunities */}
      {consolidatedMetrics?.predictions && (
        <div style={{ background: '#fff', padding: 20, borderRadius: 8, border: '1px solid #e5e7eb', marginBottom: 32 }}>
          <h3 style={{ fontSize: 18, margin: '0 0 16px 0' }}>🔮 AI Predictions & Opportunities</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, marginBottom: 16 }}>
            <div style={{ padding: 16, background: '#f0f9ff', borderRadius: 8 }}>
              <div style={{ fontSize: 14, color: '#0369a1', marginBottom: 4 }}>Next Month Prediction</div>
              <div style={{ fontSize: 20, fontWeight: 600, color: '#1e40af' }}>
                {formatCurrency(consolidatedMetrics.predictions.nextMonthSpending)}
              </div>
            </div>
            
            <div style={{ padding: 16, background: '#fef2f2', borderRadius: 8 }}>
              <div style={{ fontSize: 14, color: '#dc2626', marginBottom: 4 }}>Budget Risk</div>
              <div style={{ fontSize: 20, fontWeight: 600, color: '#b91c1c' }}>
                {formatPercentage(consolidatedMetrics.predictions.budgetRisk)}
              </div>
            </div>
          </div>

          {consolidatedMetrics.predictions.savingsOpportunities.length > 0 && (
            <div>
              <h4 style={{ fontSize: 16, margin: '0 0 12px 0' }}>💡 Savings Opportunities</h4>
              <div style={{ display: 'grid', gap: 8 }}>
                {consolidatedMetrics.predictions.savingsOpportunities.map((opp, i) => (
                  <div key={i} style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    padding: 12, 
                    background: '#f0fdf4', 
                    border: '1px solid #bbf7d0', 
                    borderRadius: 6 
                  }}>
                    <div>
                      <div style={{ fontWeight: 500, color: '#15803d' }}>{opp.category}</div>
                      <div style={{ fontSize: 12, color: '#166534' }}>
                        {formatPercentage(opp.confidence)} confidence
                      </div>
                    </div>
                    <div style={{ fontSize: 16, fontWeight: 600, color: '#059669' }}>
                      💰 {formatCurrency(opp.potentialSavings)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Quick Actions */}
      <div style={{ background: '#fff', padding: 20, borderRadius: 8, border: '1px solid #e5e7eb' }}>
        <h3 style={{ fontSize: 18, margin: '0 0 16px 0' }}>⚡ Quick Actions</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
          <a href="/transactions" style={{ 
            display: 'block', 
            padding: 12, 
            background: '#3b82f6', 
            color: 'white', 
            textDecoration: 'none', 
            borderRadius: 6, 
            textAlign: 'center', 
            fontWeight: 500 
          }}>
            📋 View Transactions
          </a>
          
          <a href="/ingest" style={{ 
            display: 'block', 
            padding: 12, 
            background: '#059669', 
            color: 'white', 
            textDecoration: 'none', 
            borderRadius: 6, 
            textAlign: 'center', 
            fontWeight: 500 
          }}>
            📁 Import Data
          </a>
          
          <a href="/live" style={{ 
            display: 'block', 
            padding: 12, 
            background: '#dc2626', 
            color: 'white', 
            textDecoration: 'none', 
            borderRadius: 6, 
            textAlign: 'center', 
            fontWeight: 500 
          }}>
            🔴 Live Dashboard
          </a>
          
          <a href="/ai" style={{ 
            display: 'block', 
            padding: 12, 
            background: '#7c3aed', 
            color: 'white', 
            textDecoration: 'none', 
            borderRadius: 6, 
            textAlign: 'center', 
            fontWeight: 500 
          }}>
            🤖 AI Features
          </a>
        </div>
      </div>

      <style jsx>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  )
}
