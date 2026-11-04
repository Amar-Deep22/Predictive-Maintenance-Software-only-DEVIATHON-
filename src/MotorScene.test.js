import { components as inspectionComponents } from './components';
import { readFileSync } from 'node:fs';
import { describe, it, expect } from 'vitest';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { Box3, Vector3 } from 'three';
import { inspectionColour, engineAsset, fittedCameraDistance } from './MotorScene';

describe('Blender digital twin', () => {
  it('fits the complete engine on narrow and wide screens', () => {
    for (const aspect of [0.5, 1, 2.5]) {
      const distance = fittedCameraDistance(aspect);
      const halfFov = Math.min(38 * Math.PI / 360, Math.atan(Math.tan(38 * Math.PI / 360) * aspect));
      expect(distance * Math.sin(halfFov)).toBeGreaterThanOrEqual(3.49);
    }
    expect(fittedCameraDistance(0.5)).toBeGreaterThan(fittedCameraDistance(2));
  });
  it('loads only the engine with movable rotors and compressor inspection metadata', async () => {
    expect(engineAsset.startsWith('/assets/')).toBe(true); // Production serves this static route.
    const bytes = readFileSync('public' + engineAsset);
    const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
    const gltf = await new GLTFLoader().parseAsync(buffer, '');
    expect(gltf.scenes).toHaveLength(1);
    expect(gltf.animations).toHaveLength(0);
    expect(gltf.parser.json.extensionsRequired || []).not.toContain('EXT_meshopt_compression');
    expect(gltf.parser.json.extensionsRequired || []).not.toContain('KHR_draco_mesh_compression');
    const components = new Set();
    let rotors = 0, shells = 0, compressor = 0;
    gltf.scene.traverse(o => {
      if (o.userData.component) components.add(o.userData.component);
      if (o.userData.rotor) rotors++;
      if (o.userData.shell) shells++;
      if (o.userData.component === 'hpc') compressor++;
    });
    expect(components.size).toBe(12);
    expect([...components].sort()).toEqual(Object.keys(inspectionComponents).sort());
    expect(inspectionComponents.bearings.sensors).toEqual([]);
    expect(inspectionComponents.hpc.sensors).toContain(3);
    expect(rotors).toBe(5);
    expect(shells).toBeGreaterThan(0);
    expect(compressor).toBeGreaterThan(0);
    const size = new Box3().setFromObject(gltf.scene).getSize(new Vector3());
    expect(size.x).toBeGreaterThan(size.y);
    expect(size.x).toBeLessThan(13);
    expect(inspectionColour({rul: 6.9, priority: 'Critical'})).toBe('#ef654b');
    expect(inspectionColour({rul: 120, priority: 'Low'})).toBe('#90ad86');
    expect(inspectionColour({rul: null, priority: 'Critical'})).toBe('#8a969e');
  });
});
