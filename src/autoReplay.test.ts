import {expect,it} from "vitest";
import {replayAutomatically,nextDemoEngine} from "./autoReplay";
it("runs sequentially until recording ends, supports stop, and propagates errors",async()=>{
  let calls=0, waiting=0;
  const final=await replayAutomatically({complete:0},async()=>({complete:++calls===3?1:0}),()=>true,async()=>{waiting++;});
  expect([calls,waiting,final.complete]).toEqual([3,2,1]);
  let active=true;
  calls=0;
  await replayAutomatically({complete:0},async()=>{calls++;return {complete:0};},()=>active,async()=>{active=false;});
  expect(calls).toBe(1);
  await expect(replayAutomatically({complete:0},async()=>{throw Error("offline");},()=>true,async()=>{})).rejects.toThrow("offline");
});

it("rotates model-selected reference engines, wraps and excludes replay duplicates and noncritical results",()=>{
 const fleet=[{id:'FD001:test:034',source:'test',rul:6.9},{id:'FD001:test:081',source:'test',rul:8.3},{id:'FD001:test:001',source:'test',rul:130},{id:'FD001:replay:034:x',source:'replay',rul:1},{id:'FD001:test:002',source:'test',rul:null}];
 expect(nextDemoEngine(fleet,null)).toBe(34);
 expect(nextDemoEngine(fleet,34)).toBe(81);
 expect(nextDemoEngine(fleet,81)).toBe(34);
 expect(nextDemoEngine([...fleet].reverse(),34)).toBe(81);
 expect(nextDemoEngine(fleet,99)).toBe(34);
 expect(nextDemoEngine([],34)).toBeNull();
});
