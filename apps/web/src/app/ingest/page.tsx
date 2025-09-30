"use client"
import { useState, useEffect } from 'react'
const API = process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000/api'

export default function Page(){
  const [result,setResult] = useState<any>(null)
  const [busy,setBusy] = useState(false)
  const [msg,setMsg] = useState('')
  const [enableAI, setEnableAI] = useState(true)
  const [aiAnalysis, setAiAnalysis] = useState<any>(null)
  const [suggestedRules, setSuggestedRules] = useState<any[]>([])
  
  async function upload(e:any, kind:'csv'|'pdf'){
    e.preventDefault()
    const file = e.target.elements.file.files[0]
    if(!file) return
    const fd = new FormData()
    fd.append('file', file)
    fd.append('enable_ai', enableAI.toString())
    setBusy(true); setMsg('Uploading…')
    const res = await fetch(`${API}/import/${kind}`, { method:'POST', body: fd })
    setBusy(false); setMsg(res.ok ? 'Upload complete' : 'Upload failed')
    const uploadResult = res.ok ? await res.json() : { error: res.status }
    setResult(uploadResult)
    
    // If AI is enabled and upload was successful, poll for AI analysis
    if(enableAI && uploadResult.run_id && uploadResult.inserted > 0) {
      setMsg('Processing with AI...')
      pollAIAnalysis(uploadResult.run_id)
    }
  }
  
  async function pollAIAnalysis(runId: string) {
    const maxAttempts = 30 // 30 seconds max
    let attempts = 0
    
    const poll = async () => {
      try {
        const res = await fetch(`${API}/import/${runId}/ai-analysis`)
        if (res.ok) {
          const analysis = await res.json()
          setAiAnalysis(analysis)
          
          if (analysis.analysis_complete) {
            setMsg('AI processing complete!')
            loadSuggestedRules(runId)
            return
          }
        }
      } catch (error) {
        console.error('Error polling AI analysis:', error)
      }
      
      attempts++
      if (attempts < maxAttempts) {
        setTimeout(poll, 1000) // Poll every second
      } else {
        setMsg('AI processing taking longer than expected...')
      }
    }
    
    poll()
  }
  
  async function loadSuggestedRules(runId: string) {
    try {
      const res = await fetch(`${API}/import/suggest-rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: runId, min_confidence: 0.7, min_transaction_count: 2 })
      })
      if (res.ok) {
        const suggestions = await res.json()
        setSuggestedRules(suggestions.suggested_rules || [])
      }
    } catch (error) {
      console.error('Error loading suggested rules:', error)
    }
  }
  
  async function createRule(rule: any) {
    try {
      const res = await fetch(`${API}/rules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rule)
      })
      if (res.ok) {
        alert('Rule created successfully!')
        // Remove from suggestions
        setSuggestedRules(prev => prev.filter(r => r.merchant !== rule.merchant))
      } else {
        alert('Failed to create rule')
      }
    } catch (error) {
      console.error('Error creating rule:', error)
      alert('Error creating rule')
    }
  }
  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ marginBottom: 24, fontSize: 28, fontWeight: 600 }}>Import Transactions</h1>
      
      {/* AI Toggle */}
      <div style={{ 
        marginBottom: 24, 
        padding: 16, 
        background: '#f8fafc', 
        border: '1px solid #e2e8f0', 
        borderRadius: 8 
      }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 500 }}>
          <input 
            type="checkbox" 
            checked={enableAI} 
            onChange={e => setEnableAI(e.target.checked)}
            style={{ transform: 'scale(1.2)' }}
          />
          🤖 Enable AI Processing
        </label>
        <p style={{ margin: '8px 0 0 28px', fontSize: 14, color: '#64748b' }}>
          Automatically enhance imported transactions with merchant normalization, category suggestions, and rule recommendations
        </p>
      </div>

      {/* Status Message */}
      {(busy || msg) && (
        <div style={{
          padding: 12, 
          background: busy ? '#fef3c7' : '#d1fae5', 
          border: `1px solid ${busy ? '#f59e0b' : '#10b981'}`, 
          borderRadius: 6,
          marginBottom: 16,
          display: 'flex',
          alignItems: 'center',
          gap: 8
        }}>
          {busy && <div style={{ 
            width: 16, 
            height: 16, 
            border: '2px solid #f59e0b', 
            borderTop: '2px solid transparent',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }} />}
          {msg}
        </div>
      )}

      {/* Upload Forms */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
        <form onSubmit={async (e)=>{e.preventDefault(); const files=(e.target as any).elements.files.files as FileList; if(!files||files.length===0)return; const fd=new FormData(); Array.from(files).forEach(f=>fd.append('files', f)); fd.append('enable_ai', enableAI.toString()); setBusy(true); setMsg('Uploading bulk…'); const res= await fetch(`${API}/import/bulk`, { method:'POST', body: fd }); setBusy(false); setMsg(res.ok ? 'Bulk upload complete' : 'Bulk upload failed'); const data = res.ok ? await res.json() : { error: res.status }; setResult(data); if(enableAI && data.run_id && data.inserted>0){ setMsg('Processing with AI...'); pollAIAnalysis(data.run_id) } }} style={{
          padding: 20,
          border: '2px dashed #94a3b8',
          borderRadius: 8,
          textAlign: 'center',
          background: '#f8fafc'
        }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>📦</div>
          <input name="files" type="file" accept=".csv,application/pdf" multiple style={{ marginBottom: 12, width: '100%' }} />
          <button type="submit" disabled={busy} style={{ padding: '10px 20px', background: '#0ea5e9', color: 'white', border: 'none', borderRadius: 6, cursor: busy ? 'not-allowed' : 'pointer', opacity: busy ? 0.5 : 1 }}>Upload Bulk</button>
        </form>
        <form onSubmit={(e)=>upload(e,'csv')} style={{
          padding: 20,
          border: '2px dashed #cbd5e1',
          borderRadius: 8,
          textAlign: 'center',
          background: '#fafafa'
        }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>📊</div>
          <input 
            name="file" 
            type="file" 
            accept=".csv" 
            style={{ marginBottom: 12, width: '100%' }}
          />
          <button 
            type="submit" 
            disabled={busy}
            style={{
              padding: '10px 20px',
              background: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: 6,
              cursor: busy ? 'not-allowed' : 'pointer',
              opacity: busy ? 0.5 : 1
            }}
          >
            Upload CSV
          </button>
        </form>
        
        <form onSubmit={(e)=>upload(e,'pdf')} style={{
          padding: 20,
          border: '2px dashed #cbd5e1',
          borderRadius: 8,
          textAlign: 'center',
          background: '#fafafa'
        }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>📄</div>
          <input 
            name="file" 
            type="file" 
            accept="application/pdf" 
            style={{ marginBottom: 12, width: '100%' }}
          />
          <button 
            type="submit" 
            disabled={busy}
            style={{
              padding: '10px 20px',
              background: '#10b981',
              color: 'white',
              border: 'none',
              borderRadius: 6,
              cursor: busy ? 'not-allowed' : 'pointer',
              opacity: busy ? 0.5 : 1
            }}
          >
            Upload PDF
          </button>
        </form>
      </div>

      {/* Upload Results */}
      {result && (
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 12, fontSize: 18, fontWeight: 600 }}>Import Results</h3>
          <div style={{
            padding: 16,
            background: '#f1f5f9',
            border: '1px solid #cbd5e1',
            borderRadius: 8,
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
            gap: 16
          }}>
            <div>
              <div style={{ fontSize: 14, color: '#64748b' }}>Inserted</div>
              <div style={{ fontSize: 20, fontWeight: 600, color: '#059669' }}>{result.inserted}</div>
            </div>
            <div>
              <div style={{ fontSize: 14, color: '#64748b' }}>Duplicates</div>
              <div style={{ fontSize: 20, fontWeight: 600, color: '#d97706' }}>{result.deduped}</div>
            </div>
            <div>
              <div style={{ fontSize: 14, color: '#64748b' }}>Raw Records</div>
              <div style={{ fontSize: 20, fontWeight: 600, color: '#6366f1' }}>{result.raw}</div>
            </div>
            <div>
              <div style={{ fontSize: 14, color: '#64748b' }}>Errors</div>
              <div style={{ fontSize: 20, fontWeight: 600, color: '#dc2626' }}>{result.errors || 0}</div>
            </div>
            {result.ai_processing && (
              <div>
                <div style={{ fontSize: 14, color: '#64748b' }}>AI Processing</div>
                <div style={{ fontSize: 20, fontWeight: 600, color: '#8b5cf6' }}>🤖 Enabled</div>
              </div>
            )}
          </div>
          
          {result.run_id && result.errors > 0 && (
            <div style={{ marginTop: 12 }}>
              <a 
                href={`${API}/import/report/${result.run_id}`} 
                target="_blank"
                style={{ color: '#dc2626', textDecoration: 'underline' }}
              >
                📥 Download error report
              </a>
            </div>
          )}
        </div>
      )}

      {/* AI Analysis Results */}
      {aiAnalysis && (
        <div style={{ marginBottom: 24 }}>
          <h3 style={{ marginBottom: 12, fontSize: 18, fontWeight: 600 }}>🤖 AI Analysis</h3>
          <div style={{
            padding: 16,
            background: '#fefce8',
            border: '1px solid #facc15',
            borderRadius: 8
          }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 16, marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 14, color: '#92400e' }}>AI Enhanced</div>
                <div style={{ fontSize: 18, fontWeight: 600 }}>{aiAnalysis.ai_enhanced_count}</div>
              </div>
              <div>
                <div style={{ fontSize: 14, color: '#92400e' }}>Quality Score</div>
                <div style={{ fontSize: 18, fontWeight: 600 }}>{(aiAnalysis.avg_quality_score * 100).toFixed(1)}%</div>
              </div>
              <div>
                <div style={{ fontSize: 14, color: '#92400e' }}>Anomalies</div>
                <div style={{ fontSize: 18, fontWeight: 600 }}>{aiAnalysis.anomalies_detected}</div>
              </div>
              <div>
                <div style={{ fontSize: 14, color: '#92400e' }}>Rule Suggestions</div>
                <div style={{ fontSize: 18, fontWeight: 600 }}>{aiAnalysis.suggested_rules_count}</div>
              </div>
            </div>
            
            {aiAnalysis.sample_ai_transactions?.length > 0 && (
              <div>
                <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8, color: '#92400e' }}>
                  Sample AI-Enhanced Transactions:
                </h4>
                <div style={{ fontSize: 12, fontFamily: 'monospace', background: '#fffbeb', padding: 8, borderRadius: 4 }}>
                  {aiAnalysis.sample_ai_transactions.slice(0, 3).map((tx: any, i: number) => (
                    <div key={i} style={{ marginBottom: 4 }}>
                      <strong>{tx.ai_merchant_name}</strong> ({(tx.confidence * 100).toFixed(0)}%) ← {tx.original_description}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Suggested Rules */}
      {suggestedRules.length > 0 && (
        <div>
          <h3 style={{ marginBottom: 12, fontSize: 18, fontWeight: 600 }}>💡 Suggested Rules</h3>
          <div style={{ display: 'grid', gap: 12 }}>
            {suggestedRules.map((rule, i) => (
              <div key={i} style={{
                padding: 16,
                background: '#f0f9ff',
                border: '1px solid #0ea5e9',
                borderRadius: 8,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>
                    "{rule.merchant}" → {rule.category_name}
                  </div>
                  <div style={{ fontSize: 14, color: '#64748b' }}>
                    {rule.reasoning}
                  </div>
                </div>
                <button
                  onClick={() => createRule(rule)}
                  style={{
                    padding: '8px 16px',
                    background: '#0ea5e9',
                    color: 'white',
                    border: 'none',
                    borderRadius: 6,
                    cursor: 'pointer',
                    marginLeft: 16
                  }}
                >
                  Create Rule
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <style jsx>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
