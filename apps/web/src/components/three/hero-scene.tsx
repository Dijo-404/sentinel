"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import { useInView } from "./use-webgl";

// Mercury tokens, mirrored here because WebGL cannot read CSS variables per frame.
const PRIMARY = new THREE.Color("#5266eb");
const PERIWINKLE = new THREE.Color("#9cb4e8");
const ON_DARK = new THREE.Color("#ededf3");

export type HeroStageRing = { key: string; count: number };

type Props = {
  stages: HeroStageRing[];
  active: number;
  reduced: boolean;
};

/** Deterministic PRNG so the starfield is identical on every load. */
function rng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296;
    return s / 4294967296;
  };
}

function glowTexture() {
  const size = 128;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const g = canvas.getContext("2d")!;
  const grad = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  grad.addColorStop(0, "rgba(255,255,255,1)");
  grad.addColorStop(0.25, "rgba(255,255,255,0.55)");
  grad.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, size, size);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

const RING_RADII = [3.3, 4.2, 5.1, 6.1];
const RING_TILTS: [number, number][] = [
  // Negative X tilt: the far arc rises above the planet instead of falling off-screen.
  [-1.36, 0.06],
  [-1.32, -0.08],
  [-1.4, 0.1],
  [-1.34, -0.04],
];

function Stars({ glow }: { glow: THREE.Texture }) {
  const ref = useRef<THREE.Points>(null);
  const geometry = useMemo(() => {
    const rand = rng(7);
    const count = 700;
    const positions = new Float32Array(count * 3);
    for (let i = 0; i < count; i += 1) {
      const r = 9 + rand() * 16;
      const theta = rand() * Math.PI * 2;
      const phi = Math.acos(2 * rand() - 1);
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = -Math.abs(r * Math.cos(phi)) - 2;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    return geo;
  }, []);
  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.z += dt * 0.004;
  });
  return (
    <points ref={ref} geometry={geometry}>
      <pointsMaterial
        size={0.09}
        map={glow}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        color={ON_DARK}
        opacity={0.7}
        sizeAttenuation
      />
    </points>
  );
}

function Rings({ stages, active, glow, reduced }: Props & { glow: THREE.Texture }) {
  const group = useRef<THREE.Group>(null);
  const ringMats = useRef<THREE.MeshBasicMaterial[]>([]);
  const lightMats = useRef<THREE.PointsMaterial[]>([]);
  const pointer = useThree((s) => s.pointer);
  const countsKey = stages.map((s) => s.count).join(",");

  // One travelling light per ~2 cases, capped so a busy stage still reads as a stream.
  const streams = useMemo(() => {
    const rand = rng(21);
    return stages.map((s) => {
      const n = Math.min(14, Math.max(3, Math.round(s.count / 2)));
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(n * 3), 3));
      return { geometry, phases: Array.from({ length: n }, () => rand()) };
    });
  }, [countsKey]);

  useFrame((state, dt) => {
    const t = reduced ? 0 : state.clock.elapsedTime;
    const g = group.current;
    if (g) {
      // Parallax toward the pointer, damped so it glides rather than snaps.
      g.rotation.y = THREE.MathUtils.damp(g.rotation.y, pointer.x * 0.35, 3, dt);
      g.rotation.x = THREE.MathUtils.damp(g.rotation.x, -pointer.y * 0.18, 3, dt);
    }
    streams.forEach((stream, i) => {
      const isActive = i === active;
      const ring = ringMats.current[i];
      if (ring) {
        ring.opacity = THREE.MathUtils.damp(ring.opacity, isActive ? 0.85 : 0.2, 6, dt);
      }
      const lights = lightMats.current[i];
      if (lights) {
        lights.size = THREE.MathUtils.damp(lights.size, isActive ? 0.42 : 0.22, 6, dt);
      }
      const r = RING_RADII[i] ?? 2;
      const speed = 0.06 + i * 0.015;
      const pos = stream.geometry.attributes.position as THREE.BufferAttribute;
      stream.phases.forEach((phase, j) => {
        const a = (phase + t * speed) * Math.PI * 2;
        pos.setXYZ(j, Math.cos(a) * r, Math.sin(a) * r, 0);
      });
      pos.needsUpdate = true;
    });
  });

  return (
    <group ref={group}>
      {stages.map((stage, i) => {
        const [tx, tz] = RING_TILTS[i] ?? [1.3, 0];
        const isActive = i === active;
        return (
          <group key={stage.key} rotation={[tx, 0, tz]}>
            <mesh>
              <torusGeometry args={[RING_RADII[i] ?? 2, 0.008, 8, 160]} />
              <meshBasicMaterial
                ref={(m) => {
                  if (m) ringMats.current[i] = m;
                }}
                color={isActive ? PERIWINKLE : ON_DARK}
                transparent
                opacity={0.2}
                depthWrite={false}
              />
            </mesh>
            {streams[i] ? (
              <points geometry={streams[i].geometry}>
                <pointsMaterial
                  ref={(m) => {
                    if (m) lightMats.current[i] = m;
                  }}
                  map={glow}
                  size={0.22}
                  color={isActive ? PERIWINKLE : PRIMARY}
                  transparent
                  depthWrite={false}
                  blending={THREE.AdditiveBlending}
                  sizeAttenuation
                />
              </points>
            ) : null}
          </group>
        );
      })}
    </group>
  );
}

const ATMOSPHERE_VERT = `
varying vec3 vNormal;
varying vec3 vView;
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vNormal = normalize(normalMatrix * normal);
  vView = normalize(-mv.xyz);
  gl_Position = projectionMatrix * mv;
}`;

// Fresnel rim: bright where the surface turns away from the viewer.
const ATMOSPHERE_FRAG = `
uniform vec3 uColor;
uniform float uPower;
varying vec3 vNormal;
varying vec3 vView;
void main() {
  float rim = pow(1.0 - abs(dot(vNormal, vView)), uPower);
  gl_FragColor = vec4(uColor * rim * 1.6, rim);
}`;

const CORE_R = 2.4;

function Core({ glow, reduced }: { glow: THREE.Texture; reduced: boolean }) {
  const orb = useRef<THREE.Mesh>(null);
  const halo = useRef<THREE.Sprite>(null);
  const atmosphere = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: ATMOSPHERE_VERT,
        fragmentShader: ATMOSPHERE_FRAG,
        uniforms: {
          uColor: { value: PERIWINKLE.clone() },
          uPower: { value: 2.6 },
        },
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      }),
    [],
  );
  useFrame((state) => {
    const t = reduced ? 0 : state.clock.elapsedTime;
    if (orb.current) orb.current.rotation.y = t * 0.08;
    if (halo.current) halo.current.scale.setScalar(11 + Math.sin(t * 0.9) * 0.35);
  });
  return (
    <group>
      <sprite ref={halo} scale={11}>
        <spriteMaterial
          map={glow}
          color={PRIMARY}
          transparent
          opacity={0.42}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </sprite>
      <mesh ref={orb}>
        <icosahedronGeometry args={[CORE_R, 12]} />
        <meshStandardMaterial
          color="#232542"
          emissive={PRIMARY}
          emissiveIntensity={0.06}
          roughness={0.5}
          metalness={0.35}
        />
      </mesh>
      <mesh scale={1.04} material={atmosphere}>
        <icosahedronGeometry args={[CORE_R, 12]} />
      </mesh>
    </group>
  );
}

export default function HeroScene(props: Props) {
  const wrap = useRef<HTMLDivElement>(null);
  const inView = useInView(wrap);
  const glow = useMemo(() => glowTexture(), []);
  return (
    <div ref={wrap} className="hero-scene" aria-hidden="true">
      <Canvas
        dpr={[1, 1.75]}
        frameloop={!inView ? "never" : props.reduced ? "demand" : "always"}
        camera={{ position: [0, 0, 10], fov: 38 }}
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: "high-performance",
        }}
      >
        <ambientLight intensity={0.4} />
        <directionalLight position={[-3, 6, 4]} intensity={2.4} color="#c9cdf5" />
        <pointLight position={[5, 0, 4]} intensity={40} color="#5266eb" />
        <Stars glow={glow} />
        {/* Planet rises from the bottom edge so the headline sits on clear sky. */}
        <group position={[0, -4.5, -1]}>
          <Core glow={glow} reduced={props.reduced} />
          <Rings {...props} glow={glow} />
        </group>
      </Canvas>
    </div>
  );
}
