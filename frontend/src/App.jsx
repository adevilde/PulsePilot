import { useEffect, useMemo, useState } from 'react'
import { fetchInsight, fetchPersonas, postFeedback, uploadDataset } from './api'
import Drivers from './components/Drivers'
import FeedbackPanel from './components/FeedbackPanel'
import MetricTable from './components/MetricTable'

export default function App() {
  const [personas, setPersonas] = useState([])
  const [contextOptions, setContextOptions] = useState([])
  const [selectedPersona, setSelectedPersona] = useState('runner')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [lastTag, setLastTag] = useState('')
  const [importMessage, setImportMessage] = useState('')
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    refreshPersonas()
  }, [])

  useEffect(() => {
    if (selectedPersona) loadInsight(selectedPersona, lastTag ? [lastTag] : [])
  }, [selectedPersona])

  async function refreshPersonas(nextSelected = null) {
    try {
      const data = await fetchPersonas()
      setPersonas(data.personas)
      setContextOptions(data.contextOptions)
      if (nextSelected) {
        setSelectedPersona(nextSelected)
      } else if (!data.personas.find((persona) => persona.key === selectedPersona)) {
        setSelectedPersona(data.personas[0]?.key || '')
      }
    } catch (err) {
      setError(err.message)
    }
  }

  async function loadInsight(personaKey, contextTags = []) {
    setLoading(true)
    setError('')
    try {
      const data = await fetchInsight(personaKey, contextTags)
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleFeedback(payload) {
    await postFeedback(payload)
    setLastTag(payload.tag)
    await loadInsight(selectedPersona, payload.tag ? [payload.tag] : [])
  }

  async function handleUpload(event) {
    const file = event.target.files?.[0]
    if (!file) return
    setUploading(true)
    setImportMessage('')
    setError('')
    try {
      const imported = await uploadDataset(file)
      const firstProfile = imported.profiles[0]?.key
      const profileCount = imported.profiles.length
      const label = profileCount === 1 ? 'profile' : 'profiles'
      setImportMessage(`Imported ${profileCount} ${label} from ${imported.datasetName}.`)
      await refreshPersonas(firstProfile)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
      event.target.value = ''
    }
  }

  const learningSummary = useMemo(() => {
    const adjustments = result?.scoredInsight?.adjustments || {}
    return Object.entries(adjustments).map(([key, value]) => `${key.replaceAll('_', ' ')} ×${value}`)
  }, [result])

  return (
    <div className="page">
      <header>
        <div>
          <h1>PulsePilot</h1>
          <p>Preventive-health copilot for wearable data, with FastAPI scoring, React UI, and optional local Mistral 7B via llama.cpp.</p>
        </div>
        <div className="button-row">
          {personas.map((persona) => (
            <button key={persona.key} className={selectedPersona === persona.key ? 'active' : ''} onClick={() => setSelectedPersona(persona.key)}>
              {persona.name}
            </button>
          ))}
        </div>
      </header>

      <section className="card">
        <h3>Import your dataset</h3>
        <p className="small">Upload a CSV with a date column and any wearable metrics you have, such as heart rate, HRV, sleep, steps, strain, stress score, or sleep score. PulsePilot will map common column names automatically and create one or more imported profiles.</p>
        <input type="file" accept=".csv" onChange={handleUpload} disabled={uploading} />
        {uploading && <p className="small">Importing dataset…</p>}
        {importMessage && <p className="small">{importMessage}</p>}
      </section>

      {loading && <div className="card">Running feature engineering, baseline scoring, and explanation layer…</div>}
      {error && <div className="card error">{error}</div>}

      {result && !loading && (
        <main className="grid">
          <section className="stack">
            <div className="card hero">
              <div className={`status ${result.explanation.status}`}>{result.explanation.status.replaceAll('_', ' ')}</div>
              <h2>{result.scoredInsight.primaryLabel}</h2>
              <p>{result.explanation.summary}</p>
              <div className="small">Engine score {result.scoredInsight.totalScore.toFixed(1)} / 100 · Confidence {(result.explanation.confidence * 100).toFixed(0)}% · Source {result.explanation.source}</div>
            </div>

            <div className="card">
              <h3>Actions today</h3>
              <ul>{result.explanation.actions.map((item) => <li key={item}>{item}</li>)}</ul>
              <h4>Seek care if</h4>
              <ul>{result.explanation.seekCare.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>

            <div className="card">
              <h3>Learning from you</h3>
              {learningSummary.length ? (
                <div className="chips">{learningSummary.map((item) => <span className="chip active" key={item}>{item}</span>)}</div>
              ) : (
                <p className="small">No personalized corrections yet.</p>
              )}
              <ul>{result.explanation.notes.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>

            <FeedbackPanel contextOptions={contextOptions} selectedPersona={selectedPersona} onSave={handleFeedback} />
          </section>

          <section className="stack">
            <Drivers drivers={result.scoredInsight.topDrivers} labels={result.persona.labels} />
            <MetricTable metrics={result.scoredInsight.metrics} labels={result.persona.labels} units={result.persona.units} />
            <div className="card">
              <h3>Scoring windows</h3>
              <p className="small">Baseline: {result.scoredInsight.featureOutput.baselineWindow[0]} → {result.scoredInsight.featureOutput.baselineWindow.at(-1)}</p>
              <p className="small">Current: {result.scoredInsight.featureOutput.currentWindow[0]} → {result.scoredInsight.featureOutput.currentWindow.at(-1)}</p>
            </div>
          </section>
        </main>
      )}
    </div>
  )
}
