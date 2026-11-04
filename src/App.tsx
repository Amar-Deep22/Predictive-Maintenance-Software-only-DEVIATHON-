import { useState } from "react";
import { Box, Cpu, Activity, Bell, ClipboardList, Gauge, Play } from "lucide-react";
import PredictiveMaintenance from "./PredictiveMaintenance";
const navigation = [
  {name:"Machines",icon:Cpu},
  {name:"3D Digital Twin",icon:Box}, {name:"Sensor Trends",icon:Activity},
  {name:"Fault Alerts",icon:Bell}, {name:"Maintenance Reports",icon:ClipboardList},
  {name:"Model Evaluation",icon:Gauge}, {name:"Sensor Replay",icon:Play},
];
const labels:Record<string,string>={"Sensor Replay":"Run a demo","Maintenance Reports":"Work orders","Model Evaluation":"Model results"};
export default function App(){
 const [page,setPage]=useState("Sensor Replay");
 const navigate=(next:string)=>{setPage(next);window.scrollTo({top:0,behavior:"instant"});};
 return <div className="app-shell">
  <aside className="sidebar"><a className="brand" href="#" aria-label="Anuraksana home" onClick={e=>{e.preventDefault();navigate("Machines");}}><span className="brand-symbol"><Box size={27}/></span></a>
  <nav>{navigation.map(n=><button key={n.name} title={n.name} aria-label={n.name} aria-current={page===n.name?"page":undefined} className={page===n.name?"nav-item active":"nav-item"} onClick={()=>{navigate(n.name);}}><n.icon size={18}/><span>{labels[n.name]??n.name}</span></button>)}</nav></aside>
  <div className="main-shell"><header className="topbar"><span className="topbar-brand">Anuraksana<span> / ML Operations</span></span><div className="breadcrumb">Workspace / <span>{page}</span></div><div className="topbar-right"><a className="guide-link" href="http://127.0.0.1:8990" target="_blank" rel="noreferrer" style={{background: "rgba(56, 189, 248, 0.15)", borderColor: "rgba(56, 189, 248, 0.4)", color: "#0284c7", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: "4px"}}>🤖 AI Agent Hub ↗</a><a className="guide-link" href="/assets/portal-guide.html" target="_blank" rel="noreferrer">User guide ↗</a><span className="offline-pill">FD001 MODEL</span></div></header>
   <main><div className="page-heading" key={page}><div><div className="eyebrow">PREDICTIVE MAINTENANCE · NASA FD001</div><h1>{labels[page]??page}</h1></div></div>
    <p className="simulation-notice">Demo: NASA FD001 uses simulated turbofan sensor data, not live hardware. Remaining life is in operating cycles. Compressor inspection is an FD001 scenario recommendation, not a confirmed diagnosis.</p>
    <PredictiveMaintenance page={page} navigate={navigate}/>
    <footer>NASA FD001 demo · Remaining life is estimated in operating cycles</footer>
   </main>
  </div>
 </div>;
}
