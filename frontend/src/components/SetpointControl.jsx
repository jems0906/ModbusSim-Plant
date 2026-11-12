import { useEffect, useState } from 'react';
import { Check } from 'lucide-react';

export default function SetpointControl({ label, name, value, min, max, unit }) {
  const [draft, setDraft] = useState('');
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { if (!editing) setDraft(value == null ? '' : String(value)); }, [value, editing]);
  async function submit(event) {
    event.preventDefault();
    if (draft.trim() === '' || !Number.isFinite(Number(draft))) { setError('Enter a valid value.'); return; }
    try {
      const response = await fetch(`/api/setpoints/${name}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ value: Number(draft) }) });
      if (!response.ok) { const result = await response.json(); throw new Error(result.detail || 'Write rejected'); }
      setEditing(false); setError('');
    } catch (problem) { setError(problem.message || 'Connection failed'); }
  }
  return <form className="setpoint" onSubmit={submit}>
    <label htmlFor={name}>{label}<span>SETPOINT</span></label>
    <div className="setpoint-entry"><input id={name} type="number" min={min} max={max} step="0.1" value={draft} onChange={event => { setEditing(true); setDraft(event.target.value); }} /><span>{unit}</span><button aria-label={`Apply ${label} setpoint`} title="Apply setpoint"><Check size={16} /></button></div>
    {error && <div role="alert" className="error">{error}</div>}
  </form>;
}