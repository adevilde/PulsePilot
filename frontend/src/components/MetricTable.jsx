export default function MetricTable({ metrics, labels, units }) {
  return (
    <div className="card">
      <h3>Metrics vs baseline</h3>
      <div className="table">
        <div className="row header"><div>Metric</div><div>Baseline</div><div>Current</div><div>Δ</div></div>
        {metrics.map((metric) => {
          const unit = units[metric.metric] ? ` ${units[metric.metric]}` : ''
          const delta = `${metric.changePct > 0 ? '+' : ''}${metric.changePct.toFixed(1)}%`
          return (
            <div className="row" key={metric.metric}>
              <div>{labels[metric.metric]}</div>
              <div>{metric.baselineMean.toFixed(1)}{unit}</div>
              <div>{metric.currentMean.toFixed(1)}{unit}</div>
              <div>{delta}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
