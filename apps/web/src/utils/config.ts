export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000/api').replace(/\/$/, '')

export const WS_URL = (() => {
  const fromEnv = process.env.NEXT_PUBLIC_WS_URL
  if (fromEnv) return fromEnv
  // Derive from API_BASE by swapping protocol and appending realtime connect
  try {
    const u = new URL(API_BASE)
    const wsProto = u.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${wsProto}//${u.host}${u.pathname}/realtime/connect`
  } catch {
    return 'ws://127.0.0.1:8000/api/realtime/connect'
  }
})()

export const UI_V1_COMPLETE = (() => {
  const v = process.env.NEXT_PUBLIC_LEDGERLOOP_UI_V1_COMPLETE
  if (!v) return false
  return v === '1' || v?.toLowerCase() === 'true'
})()
