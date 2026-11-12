import { useEffect, useState } from 'react';
import { Activity, AlarmClock, Check, CircleAlert, Radio, ShieldCheck, Siren } from 'lucide-react';
import './audit.css';

const priorities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];
const time = value => value ? new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--';
const auditLabel = event => event.category === 'connection'
  ? `Client connection ${event.event}`
  : event.event === 'response'
    ? event.is_exception ? `Exception response ${event.exception_code}` : `${event.function} response`
    : `${event.function} ${event.is_write ? 'write request' : 'request'}`;
const auditTarget = event => event.address ? `Address ${event.address}` : event.category === 'connection' ? 'Peer identity unavailable' : '';

export default function App() {
  const [snapshot, setSnapshot] = useState({ values: {}, health: {}, alarms: [], read_only: true });
  const [events, setEvents] = useState([]);
  const [securityStatus, setSecurityStatus] = useState(null);
  const [securityFindings, setSecurityFindings] = useState([]);
  const [auditStreams, setAuditStreams] = useState({ all: [], writes: [], connections: [] });
  const [auditHealth, setAuditHealth] = useState({});
  const [eventView, setEventView] = useState('alarms');
  const [auditKind, setAuditKind] = useState('all');
  const [connected, setConnected] = useState(false);
  const [filter, setFilter] = useState('ALL');
  const [actor, setActor] = useState('operator');
  const [error, setError] = useState('');

  async function loadEvents() {
    try { const response = await fetch('/api/events?limit=80'); if (response.ok) setEvents(await response.json()); }
    catch { /* WebSocket status reports backend availability. */ }
  }
  async function loadAudit() {
    try {
      const kinds = ['all', 'writes', 'connections'];
      const responses = await Promise.all(kinds.map(kind => fetch(`/plant-api/api/audit?limit=100&kind=${kind}`)));
      if (responses.some(response => !response.ok)) throw new Error('Audit endpoint unavailable');
      const results = await Promise.all(responses.map(response => response.json()));
      setAuditStreams(Object.fromEntries(kinds.map((kind, index) => [kind, results[index].events || []])));
      setAuditHealth(results[0].health || {});
    }
    catch { setAuditHealth({ unavailable: true }); }
  }
  async function loadSecurity() {
    try {
      const [statusResponse, findingsResponse] = await Promise.all([
        fetch('/api/security/status'), fetch('/api/security/events?limit=5')
      ]);
      if (!statusResponse.ok || !findingsResponse.ok) throw new Error('Security observations unavailable');
      setSecurityStatus(await statusResponse.json());
      setSecurityFindings(await findingsResponse.json());
    } catch { setSecurityStatus(previous => ({ ...previous, available: false, audit_connected: false })); }
  }
  useEffect(() => {
    let socket, timer, stopped = false;
    function connect() {
      socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
      socket.onopen = () => setConnected(true);
      socket.onmessage = event => setSnapshot(JSON.parse(event.data));
      socket.onclose = () => { setConnected(false); if (!stopped) timer = setTimeout(connect, 2000); };
      socket.onerror = () => socket.close();
    }
    connect(); loadEvents(); loadAudit(); loadSecurity();
    const refresh = setInterval(() => { loadEvents(); loadAudit(); loadSecurity(); }, 5000);
    return () => { stopped = true; clearTimeout(timer); clearInterval(refresh); socket?.close(); };
  }, []);

  async function acknowledge(alarmId) {
    try {
      const response = await fetch(`/api/alarms/${alarmId}/ack`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ actor }) });
      if (!response.ok) { const result = await response.json(); throw new Error(result.detail || 'Acknowledgment rejected'); }
      setError(''); await loadEvents();
    } catch (problem) { setError(problem.message || 'Could not reach AlarmaWatch'); }
  }

  const alarms = snapshot.alarms || [];
  const visibleAlarms = filter === 'ALL' ? alarms : alarms.filter(alarm => alarm.priority === filter);
  const health = snapshot.health || {};
  const visibleAuditEvents = auditStreams[auditKind] || [];
  const active = alarms.filter(alarm => alarm.phase === 'active');
  const pending = alarms.filter(alarm => alarm.phase === 'pending');
  const openCount = active.filter(alarm => !alarm.acknowledged).length;

  return <div className="shell">
    <aside className="sidebar"><div className="monogram"><Activity size={21} /></div><div className="side-name">ALARM<br />MANAGEMENT</div><div className="nav-item current"><Siren size={17} /><span>Alarm console</span></div><div className="nav-item"><Radio size={17} /><span>Source health</span></div><div className="sidebar-bottom"><ShieldCheck size={17} /><span>READ ONLY</span></div></aside>
    <main className="main"><header className="header"><div><div className="wordmark">AlarmaWatch <span>FIELD MONITOR</span></div><div className="crumb">UNIT 01 <b>/</b> ALARM CONSOLE</div></div><div className="header-status"><span className={`connection ${connected && health.connected ? 'good' : ''}`}><i />{connected && health.connected ? 'SOURCE ONLINE' : 'SOURCE OFFLINE'}</span><span className="readonly"><ShieldCheck size={14} /> PASSIVE / READ ONLY</span></div></header>
      <div className="content"><section className="intro"><div><div className="kicker">COMBINED CYCLE · SIMULATED ASSET</div><h1>Alarm console</h1><p>Current conditions, operator acknowledgments, and source health.</p></div><div className="rule-version">RULESET <strong>{snapshot.rule_version || '1.0.0'}</strong></div></section>
        <section className="totals" aria-label="Alarm summary"><div className="total critical-total"><span>UNACKNOWLEDGED</span><strong>{String(openCount).padStart(2, '0')}</strong><small>Active operator attention</small></div><div className="total"><span>ACTIVE</span><strong>{String(active.length).padStart(2, '0')}</strong><small>Alarm conditions present</small></div><div className="total"><span>ON DELAY</span><strong>{String(pending.length).padStart(2, '0')}</strong><small>Qualifying conditions</small></div><div className="total health-total"><span>MODBUS POLL</span><strong>{health.connected ? 'OK' : '--'}</strong><small>{health.read_point_count || 0} mapped values · read-only polling · {health.last_latency_ms ?? '--'} ms</small></div></section>
        <section className="alarms-panel"><div className="panel-heading"><div><span className="kicker">LIVE QUEUE</span><h2>Active alarms</h2></div><div className="filter-tabs" role="group" aria-label="Filter by priority">{['ALL', ...priorities].map(item => <button key={item} className={filter === item ? 'selected' : ''} onClick={() => setFilter(item)}>{item}</button>)}</div></div>
          {error && <div className="error" role="alert">{error}</div>}
          <div className="table-wrap"><table><thead><tr><th>PRIORITY</th><th>ALARM / POINT</th><th>VALUE</th><th>STATE</th><th>FIRST ACTIVE</th><th>ACTION</th></tr></thead><tbody>
            {visibleAlarms.map(alarm => <tr key={alarm.id}><td><span className={`priority p-${alarm.priority.toLowerCase()}`}>{alarm.priority}</span></td><td><strong className="alarm-label">{alarm.label}</strong><span className="tag">{alarm.id} · {alarm.tag} · {alarm.area}</span></td><td className="value">{typeof alarm.last_value === 'boolean' ? alarm.last_value ? 'ON' : 'OFF' : alarm.last_value ?? '--'} <small>{alarm.unit}</small></td><td><span className={`phase ${alarm.phase}`}>{alarm.phase === 'pending' ? <AlarmClock size={13} /> : <CircleAlert size={13} />}{alarm.phase === 'pending' ? 'ON DELAY' : alarm.acknowledged ? 'ACKNOWLEDGED' : 'UNACKNOWLEDGED'}</span></td><td className="timestamp">{time(alarm.active_since)}</td><td>{alarm.phase === 'active' && !alarm.acknowledged ? <button className="ack" onClick={() => acknowledge(alarm.id)} title={`Acknowledge ${alarm.label}`}><Check size={14} /> ACK</button> : <span className="no-action">--</span>}</td></tr>)}
            {!visibleAlarms.length && <tr><td className="empty" colSpan="6"><ShieldCheck size={20} /><strong>{filter === 'ALL' ? 'No active alarms' : `No ${filter.toLowerCase()} alarms`}</strong><span>Alarm history remains available below.</span></td></tr>}
          </tbody></table></div>
          <div className="panel-footer"><label htmlFor="actor">ACKNOWLEDGMENT OPERATOR</label><input id="actor" maxLength="64" value={actor} onChange={event => setActor(event.target.value)} /><span>Actions are recorded in the local event log.</span></div>
        </section>
        <section className="lower-grid"><div className="health-panel"><div className="subhead"><Radio size={17} /><div><span className="kicker">PASSIVE SOURCE CHECK</span><h2>ICS connection health</h2></div></div><dl><div><dt>Modbus TCP</dt><dd className={health.connected ? 'green' : 'red'}>{health.connected ? 'Connected' : 'Unavailable'}</dd></div><div><dt>Mode</dt><dd>Read-only polling</dd></div><div><dt>Last successful poll</dt><dd>{health.last_success_epoch ? new Date(health.last_success_epoch * 1000).toLocaleTimeString() : '--'}</dd></div><div><dt>Consecutive failures</dt><dd>{health.consecutive_failures ?? 0}</dd></div><div><dt>Latest poll error</dt><dd className="error-text">{health.last_error || 'None'}</dd></div></dl>
          <div className="security-observations"><div className="security-heading"><span className="kicker">SIMULATOR SECURITY OBSERVATIONS</span><span className={securityStatus?.audit_connected ? 'green' : 'red'}>{securityStatus?.audit_connected ? 'AUDIT LINK ONLINE' : 'AUDIT LINK UNAVAILABLE'}</span></div><div className="security-counts"><div><strong>{securityStatus?.available ? securityStatus.rejected_write_count : '--'}</strong><span>Rejected writes</span></div><div><strong>{securityStatus?.available ? securityStatus.unsupported_function_count : '--'}</strong><span>Unsupported functions</span></div><div><strong>{securityStatus?.available ? securityStatus.protocol_exception_count : '--'}</strong><span>Protocol exceptions</span></div></div><div className="finding-list">{securityFindings.length ? securityFindings.slice(0, 3).map((finding, index) => <div className="finding-row" key={`${finding.rule_id}-${finding.timestamp}-${index}`}><span className={`priority p-${finding.severity.toLowerCase()}`}>{finding.rule_id}</span><strong>{finding.summary}</strong><span>{finding.function_code == null ? '' : `FC${finding.function_code}`}{finding.address == null ? '' : ` · ${finding.address}`}</span></div>) : <div className="events-empty">{securityStatus?.audit_connected ? 'No configured security observations.' : 'Waiting for simulator audit source.'}</div>}</div><div className="scope-note">Local audit rules only. No packet capture, client identity, payload logging, blocking, or intrusion attribution.</div></div>
        </div>
          <div className="events-panel"><div className="subhead"><Activity size={17} /><div><span className="kicker">AUDIT TRAIL</span><h2>{eventView === 'alarms' ? 'Recent alarm events' : 'Modbus activity'}</h2></div></div>
            <div className="event-tabs" role="group" aria-label="Event history view"><button className={eventView === 'alarms' ? 'selected' : ''} onClick={() => setEventView('alarms')}>Alarm events</button><button className={eventView === 'modbus' ? 'selected' : ''} onClick={() => setEventView('modbus')}>Modbus activity</button></div>
            {eventView === 'modbus' && <div className="audit-filters" role="group" aria-label="Filter Modbus events">{[['all', 'All traffic'], ['writes', 'Writes & exceptions'], ['connections', 'Connections']].map(([kind, label]) => <button key={kind} className={auditKind === kind ? 'selected' : ''} onClick={() => setAuditKind(kind)}>{label}</button>)}</div>}
            <div className="event-list">{eventView === 'alarms' ? events.slice(0, 12).map((event, index) => <div className="event-row" key={`${event.timestamp}-${index}`}><span className={`event-mark ${event.event}`} /><span className="event-time">{time(event.timestamp)}</span><strong>{event.event.replaceAll('_', ' ')}</strong><span>{event.label}</span>{event.actor && <small>{event.actor}</small>}</div>) : visibleAuditEvents.slice(0, 16).map((event, index) => <div className="event-row" key={`${event.timestamp}-${index}`}><span className={`event-mark ${event.is_write || event.is_exception ? 'raised' : ''}`} /><span className="event-time">{time(event.timestamp)}</span><strong>{auditLabel(event)}</strong><span>{auditTarget(event)}{event.write_policy ? ` · ${event.write_policy.replaceAll('_', ' ')}` : ''}</span><small>{event.device_id == null ? '' : `Unit ${event.device_id}`}</small></div>)}{(eventView === 'alarms' ? events.length === 0 : visibleAuditEvents.length === 0) && <div className="events-empty">{eventView === 'alarms' ? 'No events recorded in this session.' : auditHealth.unavailable ? 'Modbus audit endpoint unavailable.' : 'No Modbus events match this filter.'}</div>}</div>
            {eventView === 'modbus' && <div className="scope-note audit-note">Function codes and mapped addresses are logged. Payload values and peer IP addresses are omitted. {auditHealth.disk_retention && `Disk retention: ${auditHealth.disk_retention}.`}</div>}
          </div></section>
        <footer><span>ALARMAWATCH · RULESET {snapshot.rule_version || '1.0.0'}</span><span>SIMULATION ONLY · NOT A SAFETY OR SECURITY CERTIFICATION</span></footer>
      </div>
    </main>
  </div>;
}