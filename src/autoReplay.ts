// Sequential batches prevent overlapping predictions and duplicate requests.
export async function replayAutomatically<T extends {complete:number}>(
  initial:T, step:(current:T)=>Promise<T>, active:()=>boolean, wait:()=>Promise<void>
) {
  let current=initial;
  while(active()&&!current.complete){
    current=await step(current);
    if(active()&&!current.complete)await wait();
  }
  return current;
}

// Curated demo candidates use existing model predictions, never ground-truth labels.
export function nextDemoEngine(fleet: {id:string;source:string;rul:number|null}[], last:number|null) {
  const candidates = fleet.filter(m=>m.source==='test' && m.rul!==null && Number.isFinite(m.rul) && m.rul<=15)
    .map(m=>({engine:Number(m.id.match(/^FD001:test:(\d+)$/)?.[1]),rul:m.rul!}))
    .filter(m=>Number.isInteger(m.engine)&&m.engine>=1&&m.engine<=100)
    .sort((a,b)=>a.rul-b.rul || a.engine-b.engine);
  const ids=[...new Set(candidates.map(m=>m.engine))];
  if(ids.length===0)return null;
  return ids[(ids.indexOf(last ?? -1)+1)%ids.length];
}
