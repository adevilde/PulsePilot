export async function fetchPersonas() {
  const res = await fetch('/api/personas')
  if (!res.ok) throw new Error('Failed to fetch personas')
  return res.json()
}

export async function fetchInsight(personaKey, contextTags = []) {
  const res = await fetch(`/api/insight/${personaKey}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ contextTags })
  })
  if (!res.ok) throw new Error('Failed to fetch insight')
  return res.json()
}

export async function postFeedback(payload) {
  const res = await fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!res.ok) throw new Error('Failed to save feedback')
  return res.json()
}

export async function uploadDataset(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch('/api/datasets/upload', {
    method: 'POST',
    body: formData
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail || 'Failed to import dataset')
  }
  return res.json()
}
