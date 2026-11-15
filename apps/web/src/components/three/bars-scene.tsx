"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef, type RefObject } from "react";
import * as THREE from "three";
import { useInView } from "./use-webgl";

const SPACING = 1;
const BAR_W = 0.58;
const BAR_DEPTH = 0.58;
/** Resting turn so side faces catch light; the pointer adds a little more. */
const BASE_YAW = -0.32;

const TONES = {
  light: {
    bar: new THREE.Color("#5266eb"),
    active: new THREE.Color("#8e9cf7"),
    floor: new THREE.Color("#edecfb"),
    hemiGround: "#c9c6f5",
    hemi: 1.5,
  },
  night: {
    bar: new THREE.Color("#5c6ff0"),
    active: new THREE.Color("#b7c8f0"),
    floor: new THREE.Color("#242436"),
    hemiGround: "#171721",
    hemi: 1.2,
  },
} as const;

export type SceneBar = { label: string; value: number };

type Props = {
  bars: SceneBar[];
  active: number | null;
  onActive: (index: number | null) => void;
  tone: "light" | "night";
  reduced: boolean;
  /** Value labels, placed over each bar's projected top every frame. */
  labelRefs: RefObject<(HTMLElement | null)[]>;
  /** Axis buttons, placed under each bar's projected front edge every frame. */
  tickRefs?: RefObject<(HTMLElement | null)[]>;
};

function fit(count: number, size: { width: number; height: number }) {
  // Leave a bar's width of margin so the turned row still fits.
  const zoom = size.width / (count * SPACING + 1.4);
  const visibleH = size.height / zoom;
  const maxH = THREE.MathUtils.clamp(visibleH * 0.5, 0.6, 5);
  return { zoom, visibleH, maxH };
}

function Rig({ count }: { count: number }) {
  const camera = useThree((s) => s.camera) as THREE.OrthographicCamera;
  const size = useThree((s) => s.size);
  useEffect(() => {
    const { zoom, visibleH } = fit(count, size);
    camera.zoom = zoom;
    const target = new THREE.Vector3(0, visibleH * 0.3, 0);
    // Raised camera (~28°) so bar tops read as surfaces, not lines.
    camera.position.set(0, target.y + 6.4, 12);
    camera.lookAt(target);
    camera.updateProjectionMatrix();
  }, [camera, size, count]);
  return null;
}

function place(
  el: HTMLElement | null | undefined,
  point: THREE.Vector3,
  size: { width: number; height: number },
) {
  if (!el) return;
  const x = ((point.x + 1) / 2) * size.width;
  const y = ((1 - point.y) / 2) * size.height;
  el.style.left = `${x.toFixed(1)}px`;
  el.style.top = `${y.toFixed(1)}px`;
  el.dataset.placed = "true";
}

function Bars({ bars, active, onActive, tone, reduced, labelRefs, tickRefs }: Props) {
  const group = useRef<THREE.Group>(null);
  const meshes = useRef<(THREE.Mesh | null)[]>([]);
  const heights = useRef<number[]>(bars.map(() => 0));
  const started = useRef<number | null>(null);
  const pointer = useThree((s) => s.pointer);
  const camera = useThree((s) => s.camera);
  const size = useThree((s) => s.size);
  const palette = TONES[tone];
  const max = Math.max(1, ...bars.map((b) => b.value));
  const { maxH } = fit(bars.length, size);
  const geometry = useMemo(() => {
    const g = new THREE.BoxGeometry(BAR_W, 1, BAR_DEPTH);
    g.translate(0, 0.5, 0);
    return g;
  }, []);
  const materials = useMemo(
    () =>
      bars.map(
        () =>
          new THREE.MeshStandardMaterial({
            color: palette.bar.clone(),
            roughness: 0.42,
            metalness: 0.05,
            emissive: palette.active.clone(),
            emissiveIntensity: 0,
          }),
      ),
    [bars.length, palette],
  );
  const scratch = useMemo(() => new THREE.Vector3(), []);

  useFrame((state, dt) => {
    if (started.current === null) started.current = state.clock.elapsedTime;
    const elapsed = state.clock.elapsedTime - started.current;
    const g = group.current;
    if (g) {
      const goalYaw = BASE_YAW + (reduced ? 0 : pointer.x * 0.16);
      g.rotation.y = THREE.MathUtils.damp(g.rotation.y, goalYaw, 4, dt);
      g.updateMatrixWorld();
    }
    bars.forEach((bar, i) => {
      const mesh = meshes.current[i];
      if (!mesh) return;
      const goal = Math.max(0.04, (bar.value / max) * maxH);
      const ready = reduced || elapsed > i * 0.07;
      const h = reduced
        ? goal
        : THREE.MathUtils.damp(heights.current[i] ?? 0, ready ? goal : 0, 5, dt);
      heights.current[i] = h;
      mesh.scale.y = h;
      mesh.updateMatrixWorld();

      const mat = materials[i];
      if (mat) {
        const on = active === i;
        mat.color.lerp(on ? palette.active : palette.bar, Math.min(1, dt * 10));
        mat.emissiveIntensity = THREE.MathUtils.damp(mat.emissiveIntensity, on ? 0.3 : 0, 10, dt);
      }

      // Geometry is unit height with its base at 0, so local y=1 is the top face.
      const label = labelRefs?.current?.[i];
      place(label, scratch.set(0, 1, 0).applyMatrix4(mesh.matrixWorld).project(camera), size);
      if (label) label.style.opacity = h > goal * 0.6 ? "1" : "0";
      place(
        tickRefs?.current?.[i],
        scratch
          .set(0, 0, BAR_DEPTH / 2 + 0.35)
          .applyMatrix4(mesh.matrixWorld)
          .project(camera),
        size,
      );
    });
  });

  return (
    <group ref={group} rotation-y={BASE_YAW}>
      <Rig count={bars.length} />
      <mesh rotation-x={-Math.PI / 2} position={[0, -0.002, 0]}>
        <planeGeometry args={[bars.length * SPACING + 0.3, 1.3]} />
        <meshStandardMaterial color={palette.floor} roughness={1} />
      </mesh>
      {bars.map((bar, i) => (
        <mesh
          key={bar.label}
          ref={(m) => {
            meshes.current[i] = m;
          }}
          geometry={geometry}
          material={materials[i]}
          position={[(i + 0.5 - bars.length / 2) * SPACING, 0, 0]}
          scale={[1, 0.001, 1]}
          onPointerOver={(e) => {
            e.stopPropagation();
            onActive(i);
          }}
          onPointerOut={() => onActive(null)}
        />
      ))}
    </group>
  );
}

export default function BarsScene(props: Props) {
  const wrap = useRef<HTMLDivElement>(null);
  const inView = useInView(wrap);
  const palette = TONES[props.tone];
  return (
    <div ref={wrap} className="bars3d__canvas">
      <Canvas
        orthographic
        dpr={[1, 2]}
        frameloop={inView ? "always" : "never"}
        camera={{ position: [0, 6, 12], zoom: 60, near: 0.1, far: 100 }}
        gl={{ antialias: true, alpha: true }}
      >
        <hemisphereLight args={["#ffffff", palette.hemiGround, palette.hemi]} />
        <directionalLight position={[-6, 10, 6]} intensity={2.4} />
        <directionalLight position={[7, 2, -3]} intensity={0.5} color="#9cb4e8" />
        <Bars {...props} />
      </Canvas>
    </div>
  );
}
