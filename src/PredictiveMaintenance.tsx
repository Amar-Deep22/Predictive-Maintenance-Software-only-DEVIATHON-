import { components } from "./components";
import { replayAutomatically, nextDemoEngine } from "./autoReplay";
import { api } from "./api";
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { Line, LineChart, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import "./predictive.css";
const MotorScene = lazy(()=>import("./MotorScene"));

function AnimatedValue({value, decimals=0}:{value:number;decimals?:number}) {
  const [display,setDisplay]=useState(value);
  useEffect(()=>{
    const media=window.matchMedia('(prefers-reduced-motion: reduce)');
    let frame=0;
    const finish=()=>{cancelAnimationFrame(frame);setDisplay(value);};
    if(media.matches){finish();return;}
    setDisplay(0);
    const start=performance.now()+280;
    const tick=(now:number)=>{
      const progress=Math.min(1,Math.max(0,(now-start)/1000));
      setDisplay(value*(1-Math.pow(1-progress,3)));
      if(progress<1)frame=requestAnimationFrame(tick);
    };
    frame=requestAnimationFrame(tick);
    media.addEventListener('change',finish);
    return()=>{cancelAnimationFrame(frame);media.removeEventListener('change',finish);};
  },[value]);
  return <span aria-label={value.toFixed(decimals)}><span aria-hidden="true">{display.toFixed(decimals)}</span></span>;
}

type Machine = { id: string; name: string; source: string; rul: number | null; score: number | null; priority: string; last_cycle: number; complete: number };
type Order = { updated_at:string; responses?:{worker:string;action:string;created_at:string}[]; id: string; machine_id: string; priority: string; rul: number; cycle: number; component: string; instructions: string; status: string; assignee: string; notes: string };
type Metrics = { test: { count: number; mae: number; rmse: number; alert_precision: number; alert_recall: number }; baseline_test: { mae: number }; evaluation: string; validation_protocol: string };
type History = { label: string; unit: string; series: {cycle: number; value: number}[]; predictions: {cycle:number; rul:number}[] };
function machineLabel(id:string){const match=id.match(/^FD001:(?:test|replay):(\d+)/);return match?`Machine ${Number(match[1]).toString().padStart(2,"0")}`:id;}
const transitions: Record<string,string[]> = {Draft:["Approved","Cancelled"],Approved:["In progress","Cancelled"],"In progress":["Completed","Cancelled"],Completed:[],Cancelled:[]};
function OrderEditor({order, save}:{order:Order;save:(o:Order)=>Promise<void>}) {
  const [draft,setDraft]=useState(order), [busy,setBusy]=useState(false), [dirty,setDirty]=useState(false);
  return <form className="fd-order" data-dirty={dirty} onChange={()=>setDirty(true)} onSubmit={async e=>{e.preventDefault();setBusy(true);try{await save(draft);}finally{setBusy(false);}}}>
    <h3>{order.id} · {machineLabel(order.machine_id)}</h3><p>{order.priority} priority · {order.rul.toFixed(1)} cycles remaining at creation · {order.component}</p>
    {order.responses?.length ? <ul aria-label="Worker responses">{order.responses.map(r=><li key={`${r.worker}:${r.action}`}><strong>{r.worker}</strong> {r.action==='ack'?'acknowledged':'started inspection'} · {new Date(r.created_at).toLocaleString()}</li>)}</ul> : <p>No worker response yet.</p>}
    <details className="fd-details"><summary>Inspection instructions</summary><p>{order.instructions.replace(/\b(?:Engine|Replay) (\d+)\b/g,(_,n:string)=>`Machine ${Number(n).toString().padStart(2,"0")}`)}</p></details><div className="fd-form-grid">
    <label>Assignee<input maxLength={100} value={draft.assignee} onChange={e=>setDraft({...draft,assignee:e.target.value})}/></label>
    <label>Status<select value={draft.status} onChange={e=>setDraft({...draft,status:e.target.value})}>{[order.status,...(transitions[order.status]||[])].map(s=><option key={s}>{s}</option>)}</select></label>
    <label>Notes<textarea maxLength={3000} value={draft.notes} onChange={e=>setDraft({...draft,notes:e.target.value})}/></label></div>
    <button className="button primary" disabled={busy}>{busy?"Saving…":"Save work order"}</button>
  </form>;
}
export default function PredictiveMaintenance({page="Machines",navigate=()=>{}}:{page?:string;navigate?:(page:string)=>void}) {
  const [inspected,setInspected]=useState("hpc");
  function inspectComponent(id:string){if(!components[id])return;setInspected(id);if(components[id].sensors.length)setSensor(String(components[id].sensors[0]));}
  const [view,setView]=useState("Isometric"),[viewTick,setViewTick]=useState(0),[cutaway,setCutaway]=useState(false),[paused,setPaused]=useState(false);
  const show=(...pages:string[])=>pages.includes(page);
  const [animate,setAnimate]=useState(()=>!window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  useEffect(()=>{
    const media=window.matchMedia('(prefers-reduced-motion: reduce)');
    const update=()=>setAnimate(!media.matches);
    media.addEventListener('change',update);
    return()=>media.removeEventListener('change',update);
  },[]);
  const [fleet,setFleet]=useState<Machine[]>([]),[orders,setOrders]=useState<Order[]>([]),[metrics,setMetrics]=useState<Metrics|null>(null);
  const [selected,setSelected]=useState(""),[sensor,setSensor]=useState("3"),[history,setHistory]=useState<History|null>(null);
  const [sensors,setSensors]=useState<{id:number;label:string}[]>([]),[limit,setLimit]=useState(5),[error,setError]=useState(""),[notice,setNotice]=useState(""),[busy,setBusy]=useState(false),[loading,setLoading]=useState(true),[engine,setEngine]=useState(34);
  async function refresh() {const [f,o,m,s]=await Promise.all([api<Machine[]>("machines"),api<Order[]>("work-orders"),api<Metrics>("model/metrics"),api<{id:number;label:string}[]>("sensors")]);setFleet(f.map(m=>({...m,name:machineLabel(m.id),priority:m.priority??"Pending"})));setOrders(o);setMetrics(m);setSensors(s);setSelected(prev=>prev||f[0]?.id||"");}
  useEffect(()=>{refresh().catch(e=>setError(e.message)).finally(()=>setLoading(false));},[]);
  useEffect(()=>{if(!selected)return;let active=true;setHistory(null);api<History>(`machines/${encodeURIComponent(selected)}/history?sensor=${sensor}`).then(h=>{if(active)setHistory(h);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[selected,sensor,fleet]);
  const [rotation,setRotation]=useState(true);
  const [lastDemoEngine,setLastDemoEngine]=useState<number|null>(()=>{
    try {const saved=Number(localStorage.getItem('meridian-last-demo-engine'));return Number.isInteger(saved)&&saved>=1&&saved<=100?saved:null;} catch {return null;}
  });
  const nextEngine=nextDemoEngine(fleet,lastDemoEngine);
  useEffect(()=>{
    if(page!=="Maintenance Reports")return;
    let active=true;
    const timer=setInterval(()=>{
      if(document.activeElement?.closest('.fd-order')||document.querySelector('.fd-order[data-dirty="true"]'))return;
      api<Order[]>("work-orders").then(o=>{if(active)setOrders(o);}).catch(e=>{if(active)setError(e.message);});
    },5000);
    return()=>{active=false;clearInterval(timer);};
  },[page]);
  useEffect(()=>{
    const related=components[inspected].sensors;
    if(page==="3D Digital Twin"&&related.length&&!related.includes(Number(sensor)))setSensor(String(related[0]));
  },[page,inspected,sensor]);
  const [stepCount,setStepCount]=useState(30);
  const [autoRunning,setAutoRunning]=useState(false);
  const [replayPhase,setReplayPhase]=useState("idle");
  const autoActive=useRef(false);
  useEffect(()=>()=>{autoActive.current=false;},[]);
  async function startAutomatic(){
    if(autoActive.current)return;
    const chosen=rotation?nextEngine:engine;
    if(chosen===null){setError("No demo candidates available. Turn off rotation to choose a machine.");return;}
    autoActive.current=true;setAutoRunning(true);setReplayPhase("starting");
    await action(async()=>{
      try {
        const initial=await api<Machine>("replay/start","POST",{engine_id:chosen});
        setEngine(chosen);
        if(rotation){setLastDemoEngine(chosen);try{localStorage.setItem('meridian-last-demo-engine',String(chosen));}catch{/* Rotation still works in this page when storage is unavailable. */}}
        setSelected(initial.id);setLastRun(null);
        const final=await replayAutomatically(initial,
          m=>{setReplayPhase("running");return runWindow(m.id,m.last_cycle,m.rul,30);},
          ()=>autoActive.current,
          ()=>new Promise<void>(resolve=>setTimeout(resolve,2000)));
        setReplayPhase(final.complete?"complete":"stopped");
      } catch(e){setReplayPhase("error");throw e;} finally {autoActive.current=false;setAutoRunning(false);}
    });
  }
  const [lastRun,setLastRun]=useState<{id:string;from:number;to:number;before:number|null;after:number|null;at:string}|null>(null);
  async function runWindow(id:string,from:number,before:number|null,count:number){
    const result=await api<Machine>(`replay/${encodeURIComponent(id)}/step`,"POST",{count});
    setLastRun({id,from:from+1,to:result.last_cycle,before,after:result.rul,at:new Date().toLocaleTimeString()});
    await refresh();setSelected(id);
    setNotice(result.rul===null?`Collected ${result.last_cycle}/30 cycles. More history is needed.`:`Inference complete at cycle ${result.last_cycle}. Predicted remaining life: ${result.rul.toFixed(1)} cycles.`);
    return result;
  }
  const machine=fleet.find(m=>m.id===selected);
  async function action(fn:()=>Promise<unknown>){setError("");setNotice("");setBusy(true);try{await fn();}catch(e){setError(e instanceof Error?e.message:"Request failed");}finally{setBusy(false);}}
  return <div className="fd-portal">
    <section hidden={!show("Sensor Replay")} className="panel fd-section" aria-label="Interactive model controls" aria-busy={busy}>
      <h2>Run a machine check</h2><p>Start replay. Watch real model predictions change as recorded readings arrive.</p>
      <label><span><input type="checkbox" checked={rotation} disabled={busy} onChange={e=>setRotation(e.target.checked)}/> Rotate demo machines automatically</span></label>
      {rotation&&<p><strong>Next replay: {nextEngine===null?"Loading demo machines...":`Machine ${String(nextEngine).padStart(2,"0")}`}</strong></p>}
      <div className="fd-start-row">
      <label>Machine number (1–100)<input disabled={busy||rotation} type="number" min={1} max={100} value={engine} onChange={e=>setEngine(Number(e.target.value))}/></label>
      <button className="button primary" disabled={busy||loading||(rotation?nextEngine===null:!Number.isInteger(engine)||engine<1||engine>100)} onClick={startAutomatic}>{autoRunning?"Replay running…":"Start automatic replay"}</button>
      {autoRunning&&<button className="button secondary" disabled={!autoActive.current} onClick={()=>{autoActive.current=false;setReplayPhase("stopping");setNotice("Stopping after the current batch. Any alert already triggered may still be delivered.");}}>Stop automatic replay</button>}
      </div><p className="fd-note">Simulated FD001 data. Rotation selects machines whose recorded endpoints the model predicts as Critical. Every replay recomputes predictions from sensor readings; results are never forced.</p>
      {replayPhase!=="idle"&&<div className={`fd-replay-animation ${autoRunning?"is-running":""} phase-${replayPhase}`} role="status" aria-live="polite">
        <span className="fd-replay-orbit" aria-hidden="true">{replayPhase==="complete"?"✓":replayPhase==="error"?"!":""}</span>
        <div><strong>{({starting:"Starting machine replay…",running:"Reading sensors and predicting…",stopping:"Finishing current batch…",complete:"Replay complete",stopped:"Replay stopped",error:"Replay interrupted"} as Record<string,string>)[replayPhase]}</strong>
        <small>{replayPhase==="starting"?"Preparing a fresh FD001 session":replayPhase==="complete"?"All available recorded readings processed":replayPhase==="error"?"Check the error below before restarting":`Processed through cycle ${lastRun?.to??0} · recorded FD001 data`}</small>
        <div className="fd-replay-track" aria-hidden="true"><span/></div>
</div>
      </div>}
      <p className="fd-note">High / Critical predictions trigger configured Telegram alerts to all three workers. Each successful start advances the rotation, including a stopped replay. Keep this page open.</p>
      <details className="fd-details"><summary>Manual controls & session details</summary>
      <button className="button primary" disabled={busy||!Number.isInteger(engine)||engine<1||engine>100} onClick={()=>action(async()=>{
        const m=await api<Machine>("replay/start","POST",{engine_id:engine});setSelected(m.id);setLastRun(null);await refresh();
        await runWindow(m.id,0,null,30);
      })}>{busy?"Processing dataset…":"Start machine and run model"}</button>
      {machine?.source==='replay'&&<>
        <p>Session: <code>{machine.id}</code></p>
        <label>Readings per step <select disabled={busy} value={stepCount} onChange={e=>setStepCount(Number(e.target.value))}><option value={1}>1 cycle</option><option value={10}>10 cycles</option><option value={30}>30 cycles</option></select></label>
        <button disabled={busy||Boolean(machine.complete)} onClick={()=>action(()=>runWindow(machine.id,machine.last_cycle,machine.rul,stepCount))}>{machine.complete?"Recording finished":"Run next step"}</button>
      </>}
      <p>Each prediction uses the latest 30 cycles. The recording ends before failure. Starting again creates a new session.</p>
      </details>
      {lastRun&&lastRun.id===selected&&<details className="fd-details"><summary>Latest prediction details</summary><p>Processed cycles {lastRun.from}–{lastRun.to} · Remaining life: {lastRun.before?.toFixed(1)??"—"} → {lastRun.after?.toFixed(1)??"Pending"} cycles · Updated {lastRun.at}</p></details>}
    </section>
    {metrics && show("Machines") && <div className="fleet-overview" aria-label="FD001 fleet summary">
      <article className="fleet-lead"><span>YOUR MAINTENANCE OUTLOOK</span><h2>Stay ahead of<br/>the next breakdown.</h2><p>From sensor signals to a clear plan of action.</p><a href="#priority-queue" onClick={()=>navigate("Machines")}>Review priority queue ↗</a></article>
      <article className="fleet-kpi accent"><span>Critical machines</span><strong><AnimatedValue value={fleet.filter(m=>m.source==='test'&&m.priority==='Critical').length}/></strong><small>Predicted life ≤15 cycles</small></article>
      <article className="fleet-kpi"><span>Reference fleet</span><strong><AnimatedValue value={fleet.filter(m=>m.source==='test').length}/><em> machines</em></strong><small>NASA C-MAPSS · FD001</small></article>
      <article className="fleet-kpi"><span>Model MAE</span><strong><AnimatedValue value={metrics.test.mae} decimals={2}/><em> cycles</em></strong><small>Official held-out test evaluation</small></article>
    </div>}

    {error&&<div role="alert" className="fd-error">{error} <button className="button secondary" onClick={()=>action(refresh)}>Retry connection</button></div>}
    {notice&&!notice.startsWith("Inference complete")&&<p role="status">{notice}</p>}{loading&&<p role="status">Loading FD001 model and fleet…</p>}
    <section hidden={!show("Machines")} id="priority-queue" className="panel fd-section"><h2>Maintenance priority</h2><p>Machines needing attention first.</p><details className="fd-details"><summary>How priority is calculated</summary><p>Critical ≤15, High ≤30, Medium ≤60, Low &gt;60 remaining cycles.</p></details>
      <label>Machines displayed <select value={limit} onChange={e=>setLimit(Number(e.target.value))}><option value={5}>Top 5 machines</option><option value={4}>Top 4 machines</option><option value={1000}>All machines</option></select></label>
      <div className="fd-table"><table><thead><tr><th>Rank</th><th>Machine</th><th>Priority</th><th>Risk index /100</th><th>Cycles observed</th><th>Remaining life</th><th>Inspection focus</th><th>Action</th></tr></thead><tbody>{fleet.slice(0,limit).map((m,i)=><tr key={m.id}><td>{i+1}</td><td><strong>{m.name}</strong><small>{m.source==='replay'?'Sensor replay':'FD001 reference'}</small></td><td><span className={`fd-priority ${m.priority.toLowerCase()}`}>{m.priority}</span></td><td>{m.score?.toFixed(1)??"Pending"}</td><td>{m.last_cycle}</td><td className="fd-life-cell"><strong>{m.rul==null?"Pending":`${m.rul.toFixed(1)} cycles`}</strong><small>{m.rul==null?"Needs 30 readings":"Estimated remaining life"}</small></td><td>High-pressure compressor<small>Dataset assumption</small></td><td><button className="button secondary" onClick={()=>{setSelected(m.id);navigate("3D Digital Twin");}}>Inspect {m.name}</button></td></tr>)}</tbody></table></div>
      <p className="fd-note">Risk index indicates urgency, not failure probability.</p>
    </section>
    {machine&&<section hidden={!show("Machines","3D Digital Twin","Sensor Trends","Sensor Replay")} className="panel fd-section"><h2>{machine.name} · current result</h2>
      <details className="fd-details"><summary>Change machine or view a saved run</summary><label>Selected machine <select disabled={busy} value={selected} onChange={e=>setSelected(e.target.value)}>{fleet.map(m=><option key={m.id} value={m.id}>{m.name} · {m.source=== "replay"?`Replay ${m.id.split(":").pop()}`:"Reference"} · {m.priority}</option>)}</select></label></details>
      {page==="3D Digital Twin"&&<>
        <div className="camera-tabs" aria-label="Camera controls">{["Isometric","Front","Side","Top"].map(v=><button key={v} className={view===v?"active":""} aria-pressed={view===v} onClick={()=>{setView(v);setViewTick(t=>t+1);}}>{v}</button>)}
        <button aria-pressed={cutaway} onClick={()=>setCutaway(v=>!v)}>Cutaway</button><button aria-pressed={paused} onClick={()=>setPaused(v=>!v)}>{paused?"Resume visual motion":"Pause visual motion"}</button></div>
        <div className="scene-container"  data-model-priority={machine.priority}>
          <Suspense fallback={<p>Loading 3D machine illustration…</p>}><MotorScene
            onInspect={inspectComponent} paused={paused}
            prediction={{rul:machine.rul,priority:machine.priority}}
            cutaway={cutaway} view={view} viewTick={viewTick}/></Suspense>
        </div>
        <div className="fd-inspection">
          <h3>Inspect a component</h3><p>Click an engine part, or choose one below. Use Cutaway to reach internal parts.</p>
          <label>Component<select value={inspected} onChange={e=>inspectComponent(e.target.value)}>{Object.entries(components).map(([id,c])=><option key={id} value={id}>{c.name}</option>)}</select></label>
          <p><strong>{components[inspected].name}</strong> — {components[inspected].guidance}</p>
          <p>Remaining life applies to the whole engine. This panel does not predict component lifetimes.</p>
          {components[inspected].sensors.length>0&&<><label>Related sensor<select value={components[inspected].sensors.includes(Number(sensor))?sensor:String(components[inspected].sensors[0])} onChange={e=>setSensor(e.target.value)}>{components[inspected].sensors.map(id=><option key={id} value={id}>{id} · {sensors.find(s=>s.id===id)?.label}</option>)}</select></label>
          {history&&components[inspected].sensors.includes(Number(sensor))?<><p>{history.label} · {history.unit}</p><div className="fd-chart"><ResponsiveContainer width="100%" height={220}><LineChart data={history.series}><CartesianGrid stroke="#e9e9e9"/><XAxis dataKey="cycle"/><YAxis domain={['auto','auto']}/><Tooltip/><Line dataKey="value" stroke="#df604b" dot={false} isAnimationActive={false}/></LineChart></ResponsiveContainer></div></>:<p>Loading related readings...</p>}</>}
        </div>
        <p>Compressor highlight follows this machine’s ML maintenance priority. FD001 assumes compressor degradation; this is an inspection focus, not a component diagnosis. Rotation is illustrative, not measured speed.</p>
      </>}
      <div className={`fd-stats fd-result-cards priority-${machine.priority.toLowerCase()}`}>
        <article><span>Remaining life</span><b>{machine.rul?.toFixed(1)??"Pending"}</b><span>operating cycles · estimate</span></article>
        <article><span>Maintenance priority</span><b className={`fd-priority ${machine.priority.toLowerCase()}`}>{machine.priority}</b><span>{machine.rul==null?"Waiting for readings":machine.rul<=30?"Arrange an inspection":"Continue monitoring"}</span></article>
        <article><span>Readings processed</span><b>{machine.last_cycle}</b><span>operating cycles</span></article>
      </div>
      <div className="fd-next-action"><span className="fd-action-label">Inspection focus</span><strong>High-pressure compressor</strong><p>Dataset recommendation · not a confirmed component fault.</p></div>
      <details className="fd-details"><summary>What does remaining life mean?</summary><p>Cycles are operating steps, not hours or days. Estimated end-of-life cycle: {machine.rul==null?"Pending":(machine.last_cycle+machine.rul).toFixed(1)}. Predictions are uncertain and may rise or fall. Inspection must determine repair or replacement; this model does not predict individual component lifetimes.</p></details>
      <div className="alert-actions">{page!=="Sensor Trends"&&<button onClick={()=>navigate("Sensor Trends")}>View trends</button>}{page!=="3D Digital Twin"&&<button onClick={()=>navigate("3D Digital Twin")}>View in 3D</button>}</div>
      <button className="button primary" disabled={busy||machine.rul==null} onClick={()=>action(async()=>{const o=await api<Order>("work-orders","POST",{machine_id:machine.id});await refresh();setNotice(`Work order ${o.id} saved on disk (${o.status}).`);})}>Create work order</button>
      {(page==="Sensor Trends"||page==="Sensor Replay")&&<><h3>Sensor history</h3><label>FD001 sensor <select value={sensor} onChange={e=>setSensor(e.target.value)}>{sensors.map(s=><option value={s.id} key={s.id}>{s.id} · {s.label}</option>)}</select></label>
      {history?<><p>{history.label} · {history.unit} · Latest reading: {history.series.at(-1)?.value??"No readings yet"} at cycle {history.series.at(-1)?.cycle??0}</p><div className="fd-chart"><ResponsiveContainer width="100%" height={240}><LineChart data={history.series}><CartesianGrid stroke="#e9e9e9"/><XAxis dataKey="cycle"/><YAxis domain={['auto','auto']}/><Tooltip/><Line dataKey="value" stroke="#df604b" dot={false} isAnimationActive={animate} animationDuration={1100} animationEasing="ease-out"/></LineChart></ResponsiveContainer></div><h3>Predicted remaining life over time</h3><div className="fd-chart"><ResponsiveContainer width="100%" height={210}><LineChart data={history.predictions}><XAxis dataKey="cycle"/><YAxis/><Tooltip/><Line dataKey="rul" stroke="#333333" dot={false} isAnimationActive={animate} animationDuration={1100} animationEasing="ease-out"/></LineChart></ResponsiveContainer></div><p className="fd-note">Prediction begins after 30 cycles. Horizontal axes: observed operating cycle. RUL vertical axis: remaining cycles.</p></>:<p>Loading sensor history…</p>}</>}
    </section>}
    {metrics&&<section hidden={!show("Model Evaluation")} className="panel fd-section"><h2>Model evaluation</h2><a className="button secondary" href="/assets/model-comparison.pptx" download>Download model comparison slide</a><p>Random Forest regressor · 30-cycle causal sensor windows · {metrics.test.count} official test machines.</p><div className="fd-stats">{[["MAE (cycles)",metrics.test.mae.toFixed(2)],["RMSE (cycles)",metrics.test.rmse.toFixed(2)],["Alert precision",`${(metrics.test.alert_precision*100).toFixed(1)}%`],["Alert recall",`${(metrics.test.alert_recall*100).toFixed(1)}%`]].map(([label,value])=><article key={label}><b>{value}</b><span>{label}</span></article>)}</div><details className="fd-details"><summary>Evaluation method & limitations</summary><p>Baseline MAE: {metrics.baseline_test.mae.toFixed(2)} cycles. Alert = predicted RUL ≤30; actual near-failure = true RUL ≤30.</p><p>{metrics.evaluation} {metrics.validation_protocol}</p><p>These aggregate errors are not a per-machine confidence interval. Test ground truth is used for evaluation only.</p></details><a className="button secondary" href="/api/model/predictions.csv" download>Download evaluation CSV</a></section>}
    {page==="Fault Alerts"&&<section className="panel fd-section"><h2>Which machines need attention?</h2>
      <p>Prioritized by shortest predicted remaining life. These are model-based inspection recommendations, not confirmed failures or automatic replacement decisions.</p>
      <div className="fd-stats"><article><b>{fleet.filter(m=>m.rul!==null&&m.rul<=15).length}</b><span>Critical · urgent engineering review</span></article><article><b>{fleet.filter(m=>m.rul!==null&&m.rul>15&&m.rul<=30).length}</b><span>High · plan inspection promptly</span></article><article><b>{fleet.filter(m=>m.rul===null).length}</b><span>Pending · insufficient history</span></article></div>
      {fleet.filter(m=>m.rul!==null&&m.rul<=30).sort((a,b)=>a.rul!-b.rul!).map((m,index)=><article className="fd-order" key={m.id}>
        <h3>#{index+1} · {m.name} <span className={`fd-priority ${m.priority.toLowerCase()}`}>{m.priority}</span></h3>
        <p>{m.source==="replay"?"Replay":"Reference"} · Cycle {m.last_cycle}</p>
        <div className="fd-stats"><article><b>{m.rul!.toFixed(1)}</b><span>Predicted remaining cycles</span></article><article><b>{m.score?.toFixed(1)??"—"}/100</b><span>Maintenance urgency index</span></article><article><b>{(m.last_cycle+m.rul!).toFixed(1)}</b><span>Estimated end-of-life cycle</span></article></div>
        <div className="fd-next-action"><span className="fd-action-label">Next action</span><strong>{m.rul!<=15?"Arrange urgent engineering review":"Plan an inspection soon"}</strong><p>HPC focus is a dataset assumption. Replacement requires inspection.</p></div>
        <details className="fd-details"><summary>Why this alert? View evidence</summary>
        <p><strong>Why this machine is flagged:</strong> The Random Forest model estimates {m.rul!.toFixed(1)} remaining cycles from its latest 30-cycle sensor window. This falls within the {m.rul!<=15?"critical 15-cycle":"high-priority 30-cycle"} maintenance band. This is prediction-based evidence, not a verified fault cause.</p>
        <p><strong>What needs inspection:</strong> High-pressure compressor (HPC). FD001 simulates HPC degradation; this component focus is a dataset assumption, not an independently diagnosed part failure.</p>
        <p><strong>Recommended next action:</strong> {m.rul!<=15?"Request urgent engineering review of continued operation and arrange an HPC inspection using the applicable maintenance procedure.":"Plan an HPC inspection promptly, review the sensor history and arrange maintenance resources with the responsible engineer."}</p>
        <p><strong>Does it need replacement?</strong> Not established. A qualified inspection must determine whether repair, component replacement or machine replacement is appropriate. Do not replace a machine solely because of this prediction.</p>
        <p className="fd-note">Cycles are not hours or days. Estimated life is uncertain; the urgency index is not failure probability.</p>
        <p>Session: <code>{m.id}</code></p></details>
        <div className="alert-actions"><button disabled={busy} onClick={()=>{setSelected(m.id);navigate("Sensor Trends");}}>View trends</button> <button disabled={busy} onClick={()=>{setSelected(m.id);navigate("3D Digital Twin");}}>View in 3D</button> <button className="button primary" disabled={busy} onClick={()=>action(async()=>{const o=await api<Order>("work-orders","POST",{machine_id:m.id});await refresh();setNotice(`Work order ${o.id} saved for ${m.name}.`);})}>Create work order</button></div>
      </article>)}
      {!loading&&!fleet.some(m=>m.rul!==null&&m.rul<=30)&&<p>No predictions currently fall within the 30-cycle alert band. This does not certify that machines are fault-free.</p>}
    </section>}
    <section hidden={!show("Maintenance Reports")} className="panel fd-section"><h2>Work orders ({orders.length})</h2><p>Telegram alerts create linked draft tasks. Workers can acknowledge immediately; approve an order here before they tap Start inspection. Leave Assignee blank for the first worker to claim it, or enter their configured WORKER-01 / WORKER-02 / WORKER-03 ID. Worker responses refresh every five seconds when you are not editing.</p>{orders.length===0&&<p>No work orders yet. Inspect a machine and draft a maintenance work order.</p>}{orders.map(o=><OrderEditor key={`${o.id}:${o.updated_at}`} order={o} save={draft=>action(async()=>{await api(`work-orders/${o.id}`,"PATCH",{status:draft.status,assignee:draft.assignee,notes:draft.notes,expected_updated_at:draft.updated_at});await refresh();setNotice(`${o.id} updated and saved on disk.`);})}/>)}</section>
  </div>;
}
