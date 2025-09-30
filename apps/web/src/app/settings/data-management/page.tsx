"use client"
import { useEffect, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_BASE || '/api'

interface Run {
  id?: string
  run_id?: string
  started_at: string
  files: number
  file_count?: number
  tx_count?: number
  period_start?: string | null
  period_end?: string | null
}

export default function DataManagementPage() {
  const [runs, setRuns] = useState<Run[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [files, setFiles] = useState<any[]>([])
  const [summary, setSummary] = useState<any[]>([])
  const [busy, setBusy] = useState(false)
  const [bulkFiles, setBulkFiles] = useState<FileList | null>(null)

  async function loadRuns() {
    const res = await fetch(`${API}/import/runs`)
    if (res.ok) {
      const data = await res.json()
      // normalize field name
      setRuns(data.map((r:any)=> ({...r, id: r.run_id || r.id})))
    }
  }

  async function loadRunDetails(runId: string) {
    setSelected(runId)
    const [rf, rs] = await Promise.all([
      fetch(`${API}/import/runs/${runId}/files`).then(r=>r.json()).catch(()=>[]),
      fetch(`${API}/import/runs/${runId}/summary`).then(r=>r.json()).catch(()=>[]),
    ])
    setFiles(rf)
    setSummary(rs)
  }

  async function deleteRun(runId: string) {
    if (!confirm('Delete this import and its transactions?')) return
    setBusy(true)
    const res = await fetch(`${API}/import/runs/${runId}`, { method: 'DELETE' })
    setBusy(false)
    if (res.ok) {
      await loadRuns()
      setSelected(null)
      setFiles([])
      setSummary([])
    } else {
      alert('Failed to delete')
    }
  }

  async function reprocessRun(runId: string) {
    setBusy(true)
    const res = await fetch(`${API}/import/runs/${runId}/reprocess`, { method: 'POST' })
    setBusy(false)
    if (!res.ok) alert('Failed to queue reprocess')
  }

  async function submitBulkUpload(e: any) {
    e.preventDefault()
    if (!bulkFiles || bulkFiles.length === 0) return
    setBusy(true)
    const fd = new FormData()
    Array.from(bulkFiles).forEach(f => fd.append('files', f))
    fd.append('enable_ai', 'true')
    const res = await fetch(`${API}/import/bulk`, { method: 'POST', body: fd })
    setBusy(false)
    if (res.ok) {
      await loadRuns()
      const data = await res.json()
      if (data?.run_id) await loadRunDetails(data.run_id)
    } else {
      alert('Bulk upload failed')
    }
  }

  useEffect(() => { loadRuns() }, [])

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ marginBottom: 16 }}>Data Management</h1>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 16 }}>
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8 }}>
          <div style={{ padding: 12, borderBottom: '1px solid #e5e7eb', fontWeight: 600 }}>Import Runs</div>
          <div style={{ maxHeight: 420, overflow: 'auto' }}>
            {runs.map((r) => (
              <div key={r.id} style={{ padding: 12, borderBottom: '1px solid #f3f4f6', cursor:'pointer', background: selected===r.id? '#f8fafc':'transparent' }} onClick={()=>loadRunDetails(r.id!)}>
                <div style={{ fontWeight: 600 }}>{new Date(r.started_at).toLocaleString()}</div>
                <div style={{ fontSize: 12, color: '#6b7280' }}>{(r.file_count ?? r.files) || 0} files • {r.tx_count || 0} tx</div>
                <div style={{ fontSize: 12, color: '#6b7280' }}>{r.period_start ? `${r.period_start} → ${r.period_end}` : '—'}</div>
              </div>
            ))}
          </div>

          <form onSubmit={submitBulkUpload} style={{ padding: 12, borderTop: '1px solid #e5e7eb' }}>
            <div style={{ marginBottom: 8, fontWeight: 600 }}>Bulk Upload</div>
            <input type="file" multiple onChange={e=>setBulkFiles(e.target.files)} style={{ marginBottom: 8 }} />
            <button disabled={busy} style={{ padding: '6px 12px', background:'#3b82f6', color:'#fff', border:'none', borderRadius:6 }}>{busy? 'Uploading…':'Upload'}</button>
          </form>
        </div>

        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8 }}>
          <div style={{ padding: 12, borderBottom: '1px solid #e5e7eb', display:'flex', justifyContent:'space-between', alignItems:'center' }}>
            <div style={{ fontWeight: 600 }}>Run Details</div>
            {selected && (
              <div style={{ display:'flex', gap:8 }}>
                <button onClick={()=>reprocessRun(selected)} disabled={busy} style={{ padding:'6px 10px' }}>Reprocess</button>
                <button onClick={()=>deleteRun(selected)} disabled={busy} style={{ padding:'6px 10px', color:'#fff', background:'#dc2626', border:'none', borderRadius:6 }}>Delete</button>
              </div>
            )}
          </div>
          <div style={{ padding: 12 }}>
            {selected ? (
              <>
                <h3>Files</h3>
                <table style={{ width:'100%', fontSize: 14, marginBottom: 12 }}>
                  <thead>
                    <tr style={{ borderBottom:'1px solid #e5e7eb' }}>
                      <th style={{ textAlign:'left' }}>Path</th>
                      <th>Type</th>
                      <th>Transactions</th>
                      <th>Period</th>
                    </tr>
                  </thead>
                  <tbody>
                    {files.map((f:any, i)=> (
                      <tr key={i}>
                        <td>{f.path}</td>
                        <td style={{ textAlign:'center' }}>{f.type}</td>
                        <td style={{ textAlign:'center' }}>{f.tx_count}</td>
                        <td style={{ textAlign:'center' }}>{f.period_start? `${f.period_start} → ${f.period_end}`:'—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <h3>Story by Month</h3>
                <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit,minmax(160px,1fr))', gap:8 }}>
                  {summary.map((m:any, i:number)=> (
                    <div key={i} style={{ border:'1px solid #e5e7eb', borderRadius:6, padding:8, background:'#f9fafb' }}>
                      <div style={{ fontWeight:600 }}>{new Date(m.month).toLocaleDateString(undefined, { year:'numeric', month:'short' })}</div>
                      <div style={{ fontSize:12, color:'#6b7280' }}>{m.count} tx</div>
                      <div style={{ fontSize:12, color:'#059669' }}>Income: {m.income?.toFixed?.(2) ?? m.income}</div>
                      <div style={{ fontSize:12, color:'#dc2626' }}>Spend: {m.spend?.toFixed?.(2) ?? m.spend}</div>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div style={{ color:'#6b7280' }}>Select a run to see details</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

