import SetpointControl from './SetpointControl';
import { Metric } from './TurbineOverview';

export default function HrsgOverview({ data }) {
  return <section className="area"><div className="section-heading"><div><span className="section-index">02 / HEAT RECOVERY</span><h2>HRSG &amp; feedwater</h2></div><span className="equipment-tag">HRSG-01</span></div>
    <div className="drum-reading"><div><span className="eyebrow">DRUM LEVEL</span><div className="drum-number">{data.drum_level == null ? '--' : data.drum_level.toFixed(1)} <small>%</small></div><div className="level-note"><span className="dot" /> {data.low_low_alarm ? 'Low-low trip active' : 'Operating range'}</div></div><div className="tank" aria-label={`Drum level ${data.drum_level ?? '--'} percent`}><div className="tank-water" style={{ height: `${data.drum_level || 0}%` }} /><div className="tank-line" /><span>50</span></div></div>
    <div className="metrics"><Metric label="Steam pressure" value={data.steam_pressure} unit="bar" tag="PT-201" /><Metric label="Steam temperature" value={data.steam_temp} unit="°C" tag="TT-201" /><Metric label="Feedwater flow" value={data.feedwater_flow} unit="%" tag="FT-201" /><Metric label="Steam flow" value={data.steam_flow} unit="%" tag="FT-202" /></div>
    <SetpointControl label="Drum level" name="level_setpoint" value={data.level_setpoint} min={30} max={70} unit="%" />
  </section>;
}