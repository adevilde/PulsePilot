import { useMemo, useState } from 'react'

export default function FeedbackPanel({ contextOptions, selectedPersona, onSave }) {
  const [feedbackType, setFeedbackType] = useState('accurate')
  const [tag, setTag] = useState(contextOptions[0]?.value ?? 'nothing_unusual')
  const [note, setNote] = useState('')

  const title = useMemo(() => {
    if (feedbackType === 'accurate') return 'What was it mostly related to?'
    if (feedbackType === 'not_accurate') return 'What better explains the pattern?'
    return 'Add context'
  }, [feedbackType])

  return (
    <div className="card">
      <h3>Feedback loop</h3>
      <div className="button-row">
        <button className={feedbackType === 'accurate' ? 'active' : ''} onClick={() => setFeedbackType('accurate')}>Accurate</button>
        <button className={feedbackType === 'not_accurate' ? 'active' : ''} onClick={() => setFeedbackType('not_accurate')}>Not accurate</button>
        <button className={feedbackType === 'context' ? 'active' : ''} onClick={() => setFeedbackType('context')}>Add context</button>
      </div>
      <p className="small">{title}</p>
      <div className="chips">
        {contextOptions.map((option) => (
          <button key={option.value} className={tag === option.value ? 'chip active' : 'chip'} onClick={() => setTag(option.value)}>
            {option.label}
          </button>
        ))}
      </div>
      <textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Optional note" rows={3} />
      <button onClick={() => onSave({ persona: selectedPersona, feedbackType, tag, note })}>Save feedback</button>
    </div>
  )
}
