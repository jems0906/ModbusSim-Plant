import { useEffect, useState } from 'react';
import { Activity, CirclePower, Gauge, Radio, ShieldAlert, Waves, Zap } from 'lucide-react';
import AlarmBanner from '../components/AlarmBanner';
import TurbineOverview from '../components/TurbineOverview';
import HrsgOverview from '../components/HrsgOverview';

const readOnlyDemo = import.meta.env.VITE_READ_ONLY_DEMO === '1';

export default function App() {
  const [data, setData] = useState({});
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    let socket, timer, stopped = false;
    function connect() {
      socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
      socket.onopen = () => setConnected(true);
      socket.onmessage = event => setData(JSON.parse(event.data));
      socket.onclose = () => { setConnected(false); if (!stopped) timer = setTimeout(connect, 2000); };
      socket.onerror = () => socket.close();
    }
    connect();
    return () => { stopped = true; clearTimeout(timer); socket?.close(); };
  }, []);
  async function command(path) {
    try { const response = await fetch(path, { method: 'POST' }); if (!response.ok) throw new Error('Command rejected'); setError(''); }
    catch (problem) { setError(problem.message || 'Connection failed'); }
  }
  const value = (number, unit) => number == null ? '--' : `${Number(number).toFixed(1)} ${unit}`;
  return <div className="app-shell"><aside className="rail"><div className="brand-mark"><Activity size={21} /></div><div className="rail-icons"><button className="selected" title="Plant overview" aria-label="Plant overview"><Gauge size={19} /></button><span title="Generation"><Zap size={19} /></span><span title="Heat recovery"><Waves size={19} /></span><span title="Alarms"><ShieldAlert size={19} /></span></div><div className="rail-bottom"><Radio size={18} /></div></aside>
    <main><header className="topbar"><div><div className="brand">MODBUSSIM <span>/ PLANT</span></div><div className="breadcrumb">OPERATIONS <span>/</span> UNIT OVERVIEW</div></div><div className="top-right"><span className={`connection ${connected ? 'online' : ''}`}><i />{connected ? 'LIVE CONNECTION' : 'DISCONNECTED'}</span><span className="sim-label">{readOnlyDemo ? 'PUBLIC READ-ONLY DEMO' : 'SIMULATION ONLY'}</span></div></header>
      <div className="content"><div className="page-heading"><div><div className="eyebrow">COMBINED CYCLE / UNIT 01</div><h1>Plant overview</h1><p>Real-time operations <span>•</span> Modbus TCP</p></div><div className="mode"><span>OPERATING MODE{readOnlyDemo ? ' · READ ONLY' : ''}</span><div className="mode-buttons">{['startup', 'steady', 'shutdown'].map(mode => <button key={mode} className={data.mode === mode ? 'active' : ''} disabled={readOnlyDemo} onClick={() => command(`/api/mode/${mode}`)}>{mode}</button>)}</div></div></div>
        <AlarmBanner alarm={!!data.low_low_alarm} connected={connected} onReset={() => command('/api/trip/reset')} readOnlyDemo={readOnlyDemo} />{error && <div className="command-error" role="alert">{error}</div>}
        <div className="summary"><div><span>NET GENERATION</span><strong>{value(data.generator_mw, 'MW')}</strong></div><div><span>GRID FREQUENCY</span><strong>{value(data.frequency, 'Hz')}</strong></div><div><span>BREAKER</span><strong className="status-value"><i />{data.breaker_closed == null ? '--' : data.breaker_closed ? 'CLOSED' : 'OPEN'}</strong></div><div><span>SIMULATED TIME</span><strong>{data.simulated_seconds == null ? '--' : `${Math.floor(data.simulated_seconds / 60)} min`}</strong></div></div>
        <div className="process-title"><div><h2>Process overview</h2><p>Unit 01 equipment and control</p></div><span><i /> VALUES UPDATE EVERY SECOND</span></div>
        <div className="areas"><TurbineOverview data={data} /><HrsgOverview data={data} /></div>
        <div className="equipment-strip"><div><CirclePower size={18} /><span>FEEDWATER PUMP</span><strong className={data.pump_running ? 'good' : 'bad'}>{data.pump_running == null ? '--' : data.pump_running ? 'RUNNING' : 'TRIPPED'}</strong></div><div><Waves size={18} /><span>BYPASS VALVE</span><strong>{data.bypass_open == null ? '--' : data.bypass_open ? 'OPEN' : 'CLOSED'}</strong></div><div><Activity size={18} /><span>FEEDWATER VALVE</span><strong>{value(data.feedwater_valve, '%')}</strong></div><div><Zap size={18} /><span>REACTIVE POWER</span><strong>{value(data.mvar, 'MVAR')}</strong></div></div>
        <footer>MODBUSSIM PLANT <span>TRAINING SIMULATION · NOT A SAFETY SYSTEM</span></footer>
      </div></main></div>;
}