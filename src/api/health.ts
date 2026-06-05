export type BackendStatus = 'checking' | 'connected' | 'disconnected'

interface HealthResponse {
  status: string
}

export interface AIStatus {
  configured: boolean
  provider: string
  model: string
  fallback: string
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export async function checkBackendHealth(): Promise<boolean> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), 3000)

  try {
    const response = await fetch(`${apiBaseUrl}/api/health`, {
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    })
    if (!response.ok) return false

    const data = (await response.json()) as HealthResponse
    return data.status === 'ok'
  } catch {
    return false
  } finally {
    window.clearTimeout(timeout)
  }
}

export async function getAIStatus(): Promise<AIStatus> {
  const response = await fetch(`${apiBaseUrl}/api/ai/status`, {
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) throw new Error(`AI 状态接口请求失败：${response.status}`)
  return (await response.json()) as AIStatus
}
