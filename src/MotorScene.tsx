import { Component, Suspense, useEffect, useMemo, useState, type ReactNode } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Environment, Lightformer, useGLTF } from "@react-three/drei";
import * as THREE from "three";

export const engineAsset = "/assets/models/aircraft-engine-detailed.glb";
type Props = {
  onInspect: (component:string)=>void;
  paused: boolean;
  cutaway: boolean;
  view: string;
  viewTick: number;
  prediction: { rul: number | null; priority: string };
};
export function inspectionColour(prediction: Props["prediction"]) {
  if (prediction.rul === null) return "#8a969e";
  return ({ Critical: "#ef654b", High: "#eaaa40", Medium: "#c2ac54", Low: "#90ad86" } as Record<string,string>)[prediction.priority] || "#8a969e";
}
export function fittedCameraDistance(aspect: number) {
  const verticalFov = 38 * Math.PI / 180;
  const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * Math.max(aspect, 0.1));
  return 3.5 / Math.sin(Math.min(verticalFov, horizontalFov) / 2);
}
function Camera({ view, viewTick }: Pick<Props, "view" | "viewTick">) {
  const { camera, size } = useThree();
  const distance = fittedCameraDistance(size.width / Math.max(size.height, 1));
  useEffect(() => {
    const positions: Record<string, [number, number, number]> = {
      Isometric: [-7, 4, 8], Front: [-10, 0, 0], Side: [0, 1, 10], Top: [0, 10, 0.01],
    };
    camera.position.set(...(positions[view] || positions.Isometric)).normalize().multiplyScalar(distance);
    camera.lookAt(0, 0, 0);
  }, [view, viewTick, camera, distance]);
  return <OrbitControls makeDefault target={[0,0,0]} minDistance={4} maxDistance={Math.max(18, distance * 2)} enableDamping enablePan={false}/>;
}
function Aircraft({ prediction, cutaway, paused, onInspect }: Props) {
  const { scene } = useGLTF(engineAsset, false, false);
  const model = useMemo(() => {
    const clone = scene.clone(true);
    const rotors: THREE.Object3D[] = [];
    const shells: THREE.Mesh[] = [];
    const highlights: THREE.MeshStandardMaterial[] = [];
    clone.traverse(object => {
      if (object.userData.rotor) rotors.push(object);
      if (!(object instanceof THREE.Mesh)) return;
      if (object.userData.shell) shells.push(object);
      if (object.userData.component !== "hpc") return;
      const materials = (Array.isArray(object.material) ? object.material : [object.material]).map(material => material.clone());
      object.material = Array.isArray(object.material) ? materials : materials[0];
      for (const material of materials) if (material instanceof THREE.MeshStandardMaterial) highlights.push(material);
    });
    const box = new THREE.Box3().setFromObject(clone);
    const scale = 6 / box.getSize(new THREE.Vector3()).x;
    clone.scale.setScalar(scale);
    clone.position.copy(box.getCenter(new THREE.Vector3()).multiplyScalar(-scale));
    return { clone, rotors, shells, highlights };
  }, [scene]);
  const [reducedMotion, setReducedMotion] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(query.matches);
    update(); query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    for (const material of model.highlights) {
      material.emissive.set(inspectionColour(prediction));
      material.emissiveIntensity = prediction.rul === null ? 0 : 0.35;
    }
  }, [model, prediction.priority, prediction.rul]);
  useEffect(() => { for (const shell of model.shells) shell.visible = !cutaway; }, [model, cutaway]);
  useEffect(() => () => { for (const material of model.highlights) material.dispose(); }, [model]);
  useFrame((_, delta) => {
    if (paused || reducedMotion || prediction.rul === null) return;
    for (const rotor of model.rotors) rotor.rotateX(Math.min(delta, 0.05) * 0.7);
  });
  return <primitive object={model.clone} dispose={null} onClick={(event: import('@react-three/fiber').ThreeEvent<MouseEvent>)=>{
    if(event.delta>4)return;
    let object: THREE.Object3D|null=event.object;
    while(object&&!object.userData.component)object=object.parent;
    if(object?.userData.component){event.stopPropagation();onInspect(object.userData.component);}
  }}/>;
}
function Fallback() {
  return <div className="webgl-fallback" role="status"><b>3D model could not be displayed</b><p>Refresh the page and check that WebGL is enabled. ML results remain available below.</p></div>;
}
class Boundary extends Component<{ children: ReactNode }, { error: boolean }> {
  state = { error: false };
  static getDerivedStateFromError() { return { error: true }; }
  componentDidCatch(error: Error) { console.error("Digital twin rendering failed:", error); }
  render() { return this.state.error ? <Fallback/> : this.props.children; }
}
export default function MotorScene(props: Props) {
  return <Boundary><Suspense fallback={<div className="webgl-fallback" role="status">Loading detailed aircraft engine…</div>}>
    <Canvas dpr={[1,1.5]} camera={{position:[-7,4,8],fov:38}} gl={{antialias:true}} fallback={<Fallback/>}>
      <color attach="background" args={["#17212a"]}/>
      <ambientLight intensity={1}/>
      <hemisphereLight args={["#e7f2ff","#44433a",2]}/>
      <directionalLight position={[-3,7,5]} intensity={3}/>
      <directionalLight position={[4,2,-4]} intensity={2}/>
      <Environment resolution={128}>
        <Lightformer position={[0,5,0]} rotation={[Math.PI/2,0,0]} scale={[10,5,1]} intensity={3}/>
        <Lightformer position={[-5,1,0]} rotation={[0,Math.PI/2,0]} scale={[5,3,1]} intensity={2}/>
      </Environment>
      <Aircraft {...props}/><Camera view={props.view} viewTick={props.viewTick}/>
    </Canvas>
  </Suspense></Boundary>;
}
