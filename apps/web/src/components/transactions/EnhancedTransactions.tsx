'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { useAppData } from '../../contexts/AppDataContext'
import { sharedAnalytics } from '../../services/SharedAnalyticsService'
import type { Transaction } from '../../contexts/AppDataContext'
import { UI_V1_COMPLETE } from '../../utils/config'

interface EnhancedTransactionsProps {
  initialFilters?: any
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

function parseAISuggestions(transaction: Transaction) {
  // Parse AI suggestions from database JSON string
  let aiSuggestions: Array<{
    category_name: string
    category_id?: string
    confidence: number
    reasoning: string
  }> = []
  
  if (transaction.ai_category_suggestions) {
    try {
      aiSuggestions = JSON.parse(transaction.ai_category_suggestions)
    } catch (error) {
      console.warn('Failed to parse AI suggestions:', error)
    }
  }
  
  // Fallback to ai_insights if available
  if (aiSuggestions.length === 0 && transaction.ai_insights?.category_suggestions) {
    aiSuggestions = transaction.ai_insights.category_suggestions
  }
  
  return aiSuggestions
}

function AIInsightBadge({ transaction }: { transaction: Transaction }) {
  // Check if transaction has AI insights from database
  const hasAIData = transaction.ai_processed_at || transaction.ai_confidence_score || transaction.ai_merchant_name
  
  if (!hasAIData) return null

  const confidence = transaction.ai_confidence_score || 0
  const merchantName = transaction.ai_merchant_name
  
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
      <span style={{ 
        background: '#10b981', 
        color: 'white', 
        padding: '2px 6px', 
        borderRadius: 10,
        fontSize: 10,
        fontWeight: 600
      }}>
        AI {Math.round(confidence * 100)}%
      </span>
      
      {merchantName && (
        <span style={{ color: '#059669', fontStyle: 'italic' }}>
          {merchantName}
        </span>
      )}
    </div>
  )
}

function CategorySelect({ 
  value, 
  onChange, 
  categories, 
  transaction 
}: { 
  value: string
  onChange: (value: string) => void
  categories: any[]
  transaction: Transaction
}) {
  return (
    <div style={{ width: '100%' }}>
      <select 
        value={value} 
        onChange={e => onChange(e.target.value)}
        style={{ 
          width: '100%', 
          padding: '4px 8px',
          border: '1px solid #d1d5db',
          borderRadius: 4,
          fontSize: 14
        }}
      >
        <option value="">—</option>
        {categories.map(c => (
          <option key={c.id} value={c.id}>{c.name}</option>
        ))}
      </select>
      
      {(() => {
        const aiSuggestions = parseAISuggestions(transaction)
        if (aiSuggestions.length > 0) {
          const topSuggestion = aiSuggestions[0]
          return (
            <div style={{ fontSize: 11, color: '#059669', marginTop: 2 }}>
              🎯 AI suggests: {topSuggestion.category_name} 
              ({Math.round((topSuggestion.confidence || 0) * 100)}%)
              {topSuggestion.category_id && (
                <button
                  onClick={() => onChange(topSuggestion.category_id!)}
                  style={{
                    marginLeft: 8,
                    padding: '2px 6px',
                    fontSize: 10,
                    background: '#059669',
                    color: 'white',
                    border: 'none',
                    borderRadius: 3,
                    cursor: 'pointer'
                  }}
                  title="Apply AI suggestion"
                >
                  Apply
                </button>
              )}
            </div>
          )
        }
        return null
      })()}
    </div>
  )
}

function TransactionRow({ 
  transaction, 
  categories, 
  isSelected, 
  onSelect, 
  onUpdate,
  onAnalyzeAI
}: {
  transaction: Transaction
  categories: any[]
  isSelected: boolean
  onSelect: (selected: boolean) => void
  onUpdate: (updates: Partial<Transaction>) => void
  onAnalyzeAI: () => void
}) {
  return (
    <div style={{ 
      display: 'grid', 
      gridTemplateColumns: '40px 100px 1fr 100px 250px 150px 120px', 
      alignItems: 'center', 
      padding: '12px 8px', 
      borderBottom: '1px solid #f0f0f0',
      background: isSelected ? '#f0f9ff' : 'transparent',
      gap: 8
    }}>
      <input 
        type="checkbox" 
        checked={isSelected} 
        onChange={e => onSelect(e.target.checked)} 
      />
      
      <span style={{ fontSize: 13, color: '#6b7280' }}>
        {transaction.posted_at}
      </span>
      {UI_V1_COMPLETE && (
        <span title={`Lineage: tx ${transaction.id}`} style={{ fontSize: 12, color: '#6b7280' }}>📄</span>
      )}
      
      <div style={{ minWidth: 0 }}>
        <div style={{ 
          fontWeight: 500, 
          whiteSpace: 'nowrap', 
          overflow: 'hidden', 
          textOverflow: 'ellipsis'
        }}>
          {transaction.ai_merchant_name || transaction.payee || transaction.description_norm}
        </div>
        <AIInsightBadge transaction={transaction} />
      </div>
      
      <span style={{ 
        color: transaction.amount < 0 ? '#dc2626' : '#059669', 
        textAlign: 'right', 
        fontWeight: 600 
      }}>
        {formatCurrency(transaction.amount)}
      </span>
      
      <CategorySelect
        value={transaction.category_id || ''}
        onChange={(category_id) => onUpdate({ category_id })}
        categories={categories}
        transaction={transaction}
      />
      
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <button 
          title="Toggle Business" 
          onClick={() => onUpdate({ is_business: !transaction.is_business })}
          style={{ 
            background: 'transparent', 
            border: 'none', 
            cursor: 'pointer',
            fontSize: 16
          }}
        >
          {transaction.is_business ? '🏢' : '▫️'}
        </button>
        
        <button 
          title="Toggle Income" 
          onClick={() => onUpdate({ is_income: !transaction.is_income })}
          style={{ 
            background: 'transparent', 
            border: 'none', 
            cursor: 'pointer',
            fontSize: 16
          }}
        >
          {transaction.is_income ? '💹' : '▫️'}
        </button>
        
        <button 
          title="Toggle Adjustment" 
          onClick={() => onUpdate({ is_adjustment: !transaction.is_adjustment })}
          style={{ 
            background: 'transparent', 
            border: 'none', 
            cursor: 'pointer',
            fontSize: 16
          }}
        >
          {transaction.is_adjustment ? '🧮' : '▫️'}
        </button>
        
        {transaction.is_transfer && <span title="Transfer">🔄</span>}
      </div>
      
      <div style={{ display: 'flex', gap: 4 }}>
        {!transaction.ai_processed_at && (
          <button 
            onClick={onAnalyzeAI}
            style={{
              padding: '4px 8px', 
              fontSize: 12, 
              background: '#f3f4f6', 
              border: '1px solid #d1d5db', 
              borderRadius: 4,
              cursor: 'pointer'
            }}
            title="Analyze with AI"
          >
            🤖
          </button>
        )}
        {transaction.ai_processed_at && (
          <button 
            onClick={onAnalyzeAI}
            style={{
              padding: '4px 8px', 
              fontSize: 12, 
              background: '#fbbf24', 
              border: '1px solid #f59e0b', 
              borderRadius: 4,
              cursor: 'pointer'
            }}
            title="Re-analyze with AI"
          >
            🔄
          </button>
        )}
      </div>
    </div>
  )
}

function SharedAnalyticsPanel({ transactions }: { transactions: Transaction[] }) {
  const [analytics, setAnalytics] = useState<any>(null)

  useEffect(() => {
    async function loadAnalytics() {
      try {
        const insights = await sharedAnalytics.getCrossFeatureInsights()
        setAnalytics(insights)
      } catch (error) {
        console.error('Failed to load analytics:', error)
      }
    }
    
    if (transactions.length > 0) {
      loadAnalytics()
    }
  }, [transactions])

  if (!analytics) return null

  const { transactionInsights } = analytics

  return (
    <div style={{ 
      background: '#f0f9ff', 
      border: '1px solid #dbeafe', 
      borderRadius: 8, 
      padding: 16, 
      marginBottom: 16 
    }}>
      <h3 style={{ 
        fontSize: 16, 
        margin: '0 0 12px 0',
        color: '#1e40af',
        display: 'flex',
        alignItems: 'center',
        gap: 8
      }}>
        📊 Live Transaction Analytics
      </h3>
      
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', 
        gap: 12 
      }}>
        <div style={{ textAlign: 'center', padding: 8, background: '#fff', borderRadius: 6 }}>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#dc2626' }}>
            {transactionInsights.uncategorizedCount}
          </div>
          <div style={{ fontSize: 12, color: '#6b7280' }}>Uncategorized</div>
        </div>
        
        <div style={{ textAlign: 'center', padding: 8, background: '#fff', borderRadius: 6 }}>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#059669' }}>
            {transactionInsights.aiProcessedCount}
          </div>
          <div style={{ fontSize: 12, color: '#6b7280' }}>AI Processed</div>
        </div>
        
        <div style={{ textAlign: 'center', padding: 8, background: '#fff', borderRadius: 6 }}>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#f59e0b' }}>
            {Math.round(transactionInsights.averageConfidence * 100)}%
          </div>
          <div style={{ fontSize: 12, color: '#6b7280' }}>Avg Confidence</div>
        </div>
        
        <div style={{ textAlign: 'center', padding: 8, background: '#fff', borderRadius: 6 }}>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#dc2626' }}>
            {transactionInsights.anomalyCount}
          </div>
          <div style={{ fontSize: 12, color: '#6b7280' }}>Anomalies</div>
        </div>
      </div>
      
      {transactionInsights.uncategorizedCount > 0 && (
        <div style={{ 
          marginTop: 12,
          padding: 8,
          background: '#fffbeb',
          border: '1px solid #f59e0b',
          borderRadius: 6,
          fontSize: 13,
          color: '#92400e'
        }}>
          ⚠️ {transactionInsights.uncategorizedCount} transactions need categorization.
          <button 
            style={{ 
              marginLeft: 8,
              padding: '2px 6px',
              background: '#f59e0b',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              fontSize: 11,
              cursor: 'pointer'
            }}
            onClick={() => window.location.href = '/ai'}
          >
            Run AI Enhancement
          </button>
        </div>
      )}
    </div>
  )
}

export default function EnhancedTransactions({ initialFilters = {} }: EnhancedTransactionsProps) {
  const { 
    state, 
    loadTransactions, 
    updateTransaction, 
    analyzeTransactionWithAI 
  } = useAppData()
  
  const [selected, setSelected] = useState<Record<string, boolean>>({})
  const [filters, setFilters] = useState({
    start_date: '',
    end_date: '',
    include_transfers: false,
    is_business: '',
    desc: '',
    category_id: '',
    ...initialFilters
  })

  // Load transactions when filters change
  useEffect(() => {
    loadTransactions(filters)
  }, [filters])

  const selectedTransactions = useMemo(() => {
    return Object.keys(selected).filter(id => selected[id])
  }, [selected])

  const handleBulkUpdate = async (updates: Partial<Transaction>) => {
    const promises = selectedTransactions.map(id => 
      updateTransaction(id, updates)
    )
    await Promise.all(promises)
    setSelected({})
  }

  const handleBulkAIAnalysis = async () => {
    const promises = selectedTransactions.map(id => 
      analyzeTransactionWithAI(id)
    )
    await Promise.all(promises)
  }

  const handleBulkAIAnalysisFiltered = async (mode: 'unprocessed' | 'all') => {
    let transactionsToAnalyze: string[] = []
    
    if (mode === 'unprocessed') {
      // Only analyze transactions that haven't been processed
      transactionsToAnalyze = state.transactions
        .filter(tx => !tx.ai_processed_at)
        .map(tx => tx.id)
    } else if (mode === 'all') {
      // Analyze all visible transactions
      transactionsToAnalyze = state.transactions.map(tx => tx.id)
    }

    if (transactionsToAnalyze.length === 0) {
      return
    }

    // Process in batches to avoid overwhelming the system
    const batchSize = 10
    for (let i = 0; i < transactionsToAnalyze.length; i += batchSize) {
      const batch = transactionsToAnalyze.slice(i, i + batchSize)
      const promises = batch.map(id => analyzeTransactionWithAI(id))
      await Promise.all(promises)
      
      // Small delay between batches
      if (i + batchSize < transactionsToAnalyze.length) {
        await new Promise(resolve => setTimeout(resolve, 100))
      }
    }
  }

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: 24 
      }}>
        <h1 style={{ fontSize: 28, margin: 0 }}>
          💳 Enhanced Transactions
        </h1>
        
        {state.realTime.isConnected && (
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 8,
            padding: '6px 12px',
            background: '#f0fdf4',
            border: '1px solid #bbf7d0',
            borderRadius: 6,
            fontSize: 13,
            color: '#15803d'
          }}>
            <div style={{ 
              width: 6, 
              height: 6, 
              borderRadius: '50%', 
              background: '#10b981',
              animation: 'pulse 2s infinite'
            }} />
            Live Data Connected
          </div>
        )}
      </div>

      {/* Shared Analytics Panel */}
      <SharedAnalyticsPanel transactions={state.transactions} />

      {/* AI Analysis Actions */}
      <div style={{ 
        background: '#fff',
        padding: 16,
        borderRadius: 8,
        border: '1px solid #e5e7eb',
        marginBottom: 16
      }}>
        <h3 style={{ fontSize: 16, margin: '0 0 12px 0', color: '#1f2937' }}>
          🤖 AI Enhancement
        </h3>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            onClick={() => handleBulkAIAnalysisFiltered('unprocessed')}
            style={{
              padding: '8px 16px',
              background: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: 6,
              fontSize: 14,
              cursor: 'pointer',
              fontWeight: 500
            }}
          >
            🤖 Enhance Unprocessed ({state.transactions.filter(tx => !tx.ai_processed_at).length})
          </button>
          
          <button
            onClick={() => handleBulkAIAnalysisFiltered('all')}
            style={{
              padding: '8px 16px',
              background: '#f59e0b',
              color: 'white',
              border: 'none',
              borderRadius: 6,
              fontSize: 14,
              cursor: 'pointer',
              fontWeight: 500
            }}
          >
            🔄 Re-enhance All ({state.transactions.length})
          </button>
        </div>
      </div>

      {/* Filters */}
      <div style={{ 
        background: '#fff',
        padding: 16,
        borderRadius: 8,
        border: '1px solid #e5e7eb',
        marginBottom: 16
      }}>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', 
          gap: 12,
          alignItems: 'end'
        }}>
          <div>
            <label style={{ fontSize: 13, color: '#6b7280', display: 'block', marginBottom: 4 }}>
              Start Date
            </label>
            <input 
              type="date" 
              value={filters.start_date} 
              onChange={e => setFilters({ ...filters, start_date: e.target.value })}
              style={{ 
                width: '100%', 
                padding: '6px 8px',
                border: '1px solid #d1d5db',
                borderRadius: 4
              }}
            />
          </div>
          
          <div>
            <label style={{ fontSize: 13, color: '#6b7280', display: 'block', marginBottom: 4 }}>
              End Date
            </label>
            <input 
              type="date" 
              value={filters.end_date} 
              onChange={e => setFilters({ ...filters, end_date: e.target.value })}
              style={{ 
                width: '100%', 
                padding: '6px 8px',
                border: '1px solid #d1d5db',
                borderRadius: 4
              }}
            />
          </div>
          
          <div>
            <label style={{ fontSize: 13, color: '#6b7280', display: 'block', marginBottom: 4 }}>
              Description
            </label>
            <input 
              placeholder="Search descriptions..." 
              value={filters.desc} 
              onChange={e => setFilters({ ...filters, desc: e.target.value })}
              style={{ 
                width: '100%', 
                padding: '6px 8px',
                border: '1px solid #d1d5db',
                borderRadius: 4
              }}
            />
          </div>
          
          <div>
            <label style={{ fontSize: 13, color: '#6b7280', display: 'block', marginBottom: 4 }}>
              Business
            </label>
            <select 
              value={filters.is_business} 
              onChange={e => setFilters({ ...filters, is_business: e.target.value })}
              style={{ 
                width: '100%', 
                padding: '6px 8px',
                border: '1px solid #d1d5db',
                borderRadius: 4
              }}
            >
              <option value="">Any</option>
              <option value="true">Business</option>
              <option value="false">Personal</option>
            </select>
          </div>
          
          <div>
            <label style={{ fontSize: 13, color: '#6b7280', display: 'block', marginBottom: 4 }}>
              &nbsp;
            </label>
            <label style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 6,
              fontSize: 14
            }}>
              <input 
                type="checkbox" 
                checked={filters.include_transfers} 
                onChange={e => setFilters({ ...filters, include_transfers: e.target.checked })} 
              />
              Include transfers
            </label>
          </div>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedTransactions.length > 0 && (
        <div style={{ 
          background: '#f0f9ff',
          border: '1px solid #dbeafe',
          borderRadius: 8,
          padding: 12,
          marginBottom: 16,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          flexWrap: 'wrap'
        }}>
          <span style={{ fontSize: 14, fontWeight: 500, color: '#1e40af' }}>
            {selectedTransactions.length} selected
          </span>
          
          <button
            onClick={() => handleBulkUpdate({ is_business: true })}
            style={{
              padding: '6px 12px',
              background: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              fontSize: 13,
              cursor: 'pointer'
            }}
          >
            Mark Business
          </button>
          
          <button
            onClick={() => handleBulkUpdate({ is_business: false })}
            style={{
              padding: '6px 12px',
              background: '#6b7280',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              fontSize: 13,
              cursor: 'pointer'
            }}
          >
            Mark Personal
          </button>
          
          <button
            onClick={handleBulkAIAnalysis}
            style={{
              padding: '6px 12px',
              background: '#059669',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              fontSize: 13,
              cursor: 'pointer'
            }}
          >
            🤖 Analyze Selected
          </button>
          
          <button
            onClick={() => handleBulkAIAnalysisFiltered('unprocessed')}
            style={{
              padding: '6px 12px',
              background: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              fontSize: 13,
              cursor: 'pointer'
            }}
          >
            🤖 Analyze Unprocessed
          </button>
          
          <button
            onClick={() => handleBulkAIAnalysisFiltered('all')}
            style={{
              padding: '6px 12px',
              background: '#f59e0b',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              fontSize: 13,
              cursor: 'pointer'
            }}
          >
            🔄 Re-analyze All
          </button>
          
          <button
            onClick={() => setSelected({})}
            style={{
              padding: '6px 12px',
              background: '#f3f4f6',
              color: '#374151',
              border: '1px solid #d1d5db',
              borderRadius: 4,
              fontSize: 13,
              cursor: 'pointer'
            }}
          >
            Clear Selection
          </button>
        </div>
      )}

      {/* Transaction List */}
      <div style={{ 
        background: '#fff',
        borderRadius: 8,
        border: '1px solid #e5e7eb',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: '40px 100px 1fr 100px 250px 150px 120px',
          padding: '12px 8px',
          background: '#f9fafb',
          borderBottom: '1px solid #e5e7eb',
          fontWeight: 600,
          fontSize: 14,
          gap: 8
        }}>
          <input 
            type="checkbox" 
            onChange={e => {
              const newSelected: Record<string, boolean> = {}
              if (e.target.checked) {
                state.transactions.forEach(t => newSelected[t.id] = true)
              }
              setSelected(newSelected)
            }}
          />
          <div>Date</div>
          <div>Description</div>
          <div style={{ textAlign: 'right' }}>Amount</div>
          <div>Category</div>
          <div>Flags</div>
          <div>Actions</div>
        </div>
        
        {/* Rows */}
        <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
          {state.loading.transactions ? (
            <div style={{ 
              padding: 40, 
              textAlign: 'center', 
              color: '#6b7280' 
            }}>
              Loading transactions...
            </div>
          ) : state.transactions.length === 0 ? (
            <div style={{ 
              padding: 40, 
              textAlign: 'center', 
              color: '#6b7280' 
            }}>
              No transactions found
            </div>
          ) : (
            state.transactions.map(transaction => (
              <TransactionRow
                key={transaction.id}
                transaction={transaction}
                categories={state.categories}
                isSelected={!!selected[transaction.id]}
                onSelect={selected => setSelected(prev => ({ ...prev, [transaction.id]: selected }))}
                onUpdate={updates => updateTransaction(transaction.id, updates)}
                onAnalyzeAI={() => analyzeTransactionWithAI(transaction.id)}
              />
            ))
          )}
        </div>
      </div>

      {/* Footer */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginTop: 16,
        fontSize: 14,
        color: '#6b7280'
      }}>
        <div>
          {state.transactions.length} transactions loaded
          {state.errors.transactions && (
            <span style={{ color: '#dc2626', marginLeft: 8 }}>
              Error: {state.errors.transactions}
            </span>
          )}
        </div>
        
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => loadTransactions(filters)}
            style={{
              padding: '6px 12px',
              background: '#f3f4f6',
              border: '1px solid #d1d5db',
              borderRadius: 4,
              fontSize: 13,
              cursor: 'pointer'
            }}
          >
            🔄 Refresh
          </button>
          
          <a 
            href="/ingest"
            style={{
              padding: '6px 12px',
              background: '#3b82f6',
              color: 'white',
              textDecoration: 'none',
              borderRadius: 4,
              fontSize: 13
            }}
          >
            📁 Import More
          </a>
        </div>
      </div>

      <style jsx>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  )
}
