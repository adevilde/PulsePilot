export default function Drivers({ drivers, labels }) {
  return (
    <div className="card">
      <h3>Top drivers</h3>
      <div className="drivers">
        {drivers.map((driver) => (
          <div className="driver" key={driver.metric}>
            <strong>{labels[driver.metric]}</strong>
            <div>{driver.changePct > 0 ? '+' : ''}{driver.changePct.toFixed(1)}% vs baseline</div>
            <div className="small">z-score {driver.zScore.toFixed(2)} · slope {driver.slope.toFixed(2)}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
