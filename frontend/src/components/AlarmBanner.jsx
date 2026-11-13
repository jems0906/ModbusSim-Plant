import { AlertTriangle, CheckCircle2, RotateCcw } from 'lucide-react';

export default function AlarmBanner({ alarm, connected, onReset, readOnlyDemo = false }) {
  return <div className={`alarm-banner ${alarm ? 'alarm-active' : ''}`} role="status">
    <div className="alarm-main">{alarm ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}<strong>{!connected ? 'CONNECTION LOST' : alarm ? 'DRUM LEVEL LOW-LOW' : 'NO ACTIVE ALARMS'}</strong><span>{!connected ? 'Live values unavailable' : alarm ? 'Feedwater pump trip latched' : 'Plant conditions normal'}</span></div>
    {alarm && <button className="reset" disabled={readOnlyDemo} title={readOnlyDemo ? 'Trip reset is disabled in this public read-only demo' : 'Reset trip'} onClick={onReset}><RotateCcw size={14} />{readOnlyDemo ? 'Read-only' : 'Reset trip'}</button>}
    <span className="alarm-count">{alarm ? '01' : '00'} ACTIVE</span>
  </div>;
}