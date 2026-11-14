import { useEffect, useState } from 'react'
import { api, USE_FIXTURES } from '../api/client.js'
import { useT } from '../i18n/index.jsx'
import { useMission } from '../mission.jsx'

export default function Crew() {
  const { t } = useT()
  const { refresh } = useMission()
  const [crew, setCrew] = useState([])
  const [packets, setPackets] = useState([])
  const [amplitude, setAmplitude] = useState('3')
  const [comparison, setComparison] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(true)

  useEffect(() => {
    let mounted = true
    Promise.all([api.getCrew(), api.getTransmissions()])
      .then(([roster, queue]) => {
        if (mounted) {
          setCrew(roster)
          setPackets(queue)
        }
      })
      .catch(err => { if (mounted) setError(err.message) })
      .finally(() => { if (mounted) setBusy(false) })
    return () => { mounted = false }
  }, [])

  async function run(action) {
    setBusy(true)
    setError('')
    try {
      await action()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const disabled = busy || USE_FIXTURES
  const percent = rate => (rate * 100).toFixed(3) + '%'

  return (
    <section className="page">
      <h1>{t('nav.crew')}</h1>
      <ul className="panel guide">
        {crew.map(member => <li key={member.id}><strong>{member.name}</strong><span>{member.role}</span></li>)}
      </ul>
      <h2>{t('tx.title')}</h2>
      {USE_FIXTURES && <p className="muted">{t('tx.connect')}</p>}
      <div className="tx-actions">
        <button className="btn btn-secondary" disabled={disabled}
          onClick={() => run(async () => setPackets(await api.queueDailySummaries()))}>{t('tx.queue_daily')}</button>
        <button className="btn btn-secondary" disabled={disabled}
          onClick={() => run(async () => setPackets(await api.getTransmissions()))}>{t('tx.refresh')}</button>
        <button className="btn btn-secondary" disabled={disabled} onClick={() => run(async () => {
          const { clock, next_window } = await api.getMission()
          const sol = clock.sol + (next_window <= clock.time ? 1 : 0)
          await api.setDemoClock({ sol, time: next_window })
          refresh()
        })}>{t('tx.next_window')}</button>
        <button className="btn btn-primary" disabled={disabled || !packets.some(packet => ['queued', 'missing'].includes(packet.status))}
          onClick={() => run(async () => setPackets(await api.sendTransmissions()))}>{t('tx.send')}</button>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {!busy && !packets.length && <p className="muted">{t('tx.empty')}</p>}
      <label className="tx-amplitude">
        {t('tx.amplitude')}
        <input type="number" min="1.1" max="10" step="0.1" value={amplitude}
          onChange={event => setAmplitude(event.target.value)} />
      </label>
      <ul className="panel guide tx-packets" aria-live="polite">
        {packets.map(packet => (
          <li key={packet.seq}>
            <strong className="num">#{packet.seq} · {packet.crew.toUpperCase()}</strong>
            <span>{t(`tx.status.${packet.status}`)}</span>
            <p className="muted">{t('tx.attempts', { count: packet.attempts })} · <span className="num">{packet.hash.slice(0, 12)}</span></p>
            <div className="tx-actions">
              {packet.status === 'sent' && <button className="btn btn-secondary" disabled={disabled}
                onClick={() => run(async () => setPackets(await api.recordReceipt(packet.seq, 'missing', packet.attempts)))}>{t('tx.missing')}</button>}
              {(packet.status === 'sent' || packet.status === 'missing') && <button className="btn btn-secondary" disabled={disabled}
                onClick={() => run(async () => setPackets(await api.recordReceipt(packet.seq, 'acked', packet.attempts)))}>{t('tx.ack')}</button>}
              <button className="btn btn-secondary" disabled={disabled || Number(amplitude) < 1.1 || Number(amplitude) > 10}
                onClick={() => run(async () => setComparison(await api.simulateTransmission(packet.seq, Number(amplitude))))}>{t('tx.compare')}</button>
            </div>
          </li>
        ))}
      </ul>
      {comparison && <div className="panel tx-results">
        <h2>{t('tx.comparison', { seq: comparison.seq, bits: comparison.packet_bits })}</h2>
        <table>
          <thead><tr>{['amplitude', 'bit_errors', 'success', 'energy'].map(key => <th key={key} scope="col">{t(`tx.${key}`)}</th>)}</tr></thead>
          <tbody>{[comparison.narrow, comparison.wide].map(result => (
            <tr className="num" key={result.amplitude}>
              <td>±{result.amplitude}</td>
              <td>{percent(result.bit_error_rate)}</td>
              <td>{result.successful_packets} / {comparison.trials}</td>
              <td>{result.relative_energy_per_bit.toFixed(1)}×</td>
            </tr>
          ))}</tbody>
        </table>
      </div>}
    </section>
  )
}
