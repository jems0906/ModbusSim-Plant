import { AlertTriangle, CheckCircle2, RotateCcw } from 'lucide-react';

export default function AlarmBanner({ alarm, connected, onReset }) {
  return <div className={`alarm-banner ${alarm ? 'alarm-active' : ''}`} role="status">
    <div className="alarm-main">{alarm ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}<strong>{!connected ? 'CONNECTION LOST' : alarm ? 'DRUM LEVEL LOW-LOW' : 'NO ACTIVE ALARMS'}</strong><span>{!connected ? 'Live values unavailable' : alarm ? 'Feedwater pump trip latched' : 'Plant conditions normal'}</span></div>
    {alarm && <button className="reset" onClick={onReset}><RotateCcw size={14} /> Reset trip</button>}
    <span className="alarm-count">{alarm ? '01' : '00'} ACTIVE</span>
  </div>;
}