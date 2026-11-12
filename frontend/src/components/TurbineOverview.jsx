import SetpointControl from './SetpointControl';

export function Metric({ label, value, unit, decimals = 1, tag }) {
  return <div className="metric"><div className="metric-label">{label}{tag && <span>{tag}</span>}</div><div className="metric-value">{value == null ? '--' : Number(value).toFixed(decimals)} <small>{unit}</small></div></div>;
}

export default function TurbineOverview({ data }) {
  return <section className="area"><div className="section-heading"><div><span className="section-index">01 / GENERATION</span><h2>Gas turbine</h2></div><span className="equipment-tag">GT-01</span></div>
    <div className="main-reading"><span>ACTIVE LOAD</span><div>{data.gas_load == null ? '--' : data.gas_load.toFixed(1)} <small>MW</small></div><div className="reading-foot"><span>Fuel demand</span><strong>{data.fuel_valve == null ? '--' : data.fuel_valve.toFixed(1)}%</strong></div><div className="bar"><i style={{ width: `${data.fuel_valve || 0}%` }} /></div></div>
    <div className="metrics"><Metric label="Fuel flow" value={data.fuel_flow} unit="kg/s" tag="FT-101" /><Metric label="Exhaust temperature" value={data.exhaust_temp} unit="°C" tag="TT-101" /><Metric label="Rotor speed" value={data.rpm} unit="RPM" decimals={0} tag="ST-101" /><Metric label="Steam turbine load" value={data.steam_load} unit="MW" tag="ST-01" /><Metric label="Inlet pressure" value={data.steam_inlet_pressure} unit="bar" tag="PT-301" /></div>
    <SetpointControl label="Gas turbine load" name="load_setpoint" value={data.load_setpoint} min={0} max={600} unit="MW" />
  </section>;
}