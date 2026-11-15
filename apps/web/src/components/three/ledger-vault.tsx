"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";
import type { MotionValue } from "framer-motion";

// Token mirrors: WebGL cannot read CSS variables per frame.
const SIGNAL = new THREE.Color("#8b95ff");
const VERIFIED = new THREE.Color("#c6f36b");
const MIST = new THREE.Color("#ededf3");
const RINGS = [2.6, 2.1, 1.6, 1.1];

/**
 * The "ledger vault": four check rings stacked in depth. A case token falls through
 * them as the page scrolls and turns lime only after the last ring (verified).
 */
function Vault({
  progress,
  pointer,
}: {
  progress: MotionValue<number>;
  pointer: React.RefObject<{ x: number; y: number }>;
}) {
  const group = useRef<THREE.Group>(null);
  const token = useRef<THREE.Mesh>(null);
  const tokenMat = useRef<THREE.MeshStandardMaterial>(null);
  const rings = useRef<(THREE.Mesh | null)[]>([]);

  useFrame((state, dt) => {
    const p = progress.get();
    const g = group.current;
    if (g) {
      g.rotation.y += dt * 0.12;
      g.rotation.x = THREE.MathUtils.lerp(
        g.rotation.x,
        -0.55 + (pointer.current?.y ?? 0) * 0.15,
        0.05,
      );
      g.rotation.z = THREE.MathUtils.lerp(g.rotation.z, (pointer.current?.x ?? 0) * 0.15, 0.05);
      g.position.y = p * 1.6;
    }
    rings.current.forEach((m, i) => {
      if (!m) return;
      m.rotation.z += dt * (0.2 + i * 0.12) * (i % 2 ? -1 : 1);
      const passed = p * 5 > i + 1;
      (m.material as THREE.MeshStandardMaterial).emissiveIntensity = THREE.MathUtils.lerp(
        (m.material as THREE.MeshStandardMaterial).emissiveIntensity,
        passed ? 1.4 : 0.35,
        0.08,
      );
    });
    const t = token.current;
    if (t && tokenMat.current) {
      t.position.y =
        1.8 - Math.min(1, p * 1.2) * 3.6 + Math.sin(state.clock.elapsedTime * 2) * 0.05;
      tokenMat.current.color.lerp(p > 0.8 ? VERIFIED : SIGNAL, 0.06);
      tokenMat.current.emissive.copy(tokenMat.current.color);
    }
  });

  return (
    <group ref={group}>
      {RINGS.map((r, i) => (
        <mesh
          key={r}
          ref={(m) => {
            rings.current[i] = m;
          }}
          position={[0, 1.2 - i * 0.8, 0]}
          rotation={[Math.PI / 2, 0, 0]}
        >
          <torusGeometry args={[r, 0.022, 16, 160]} />
          <meshStandardMaterial
            color={i === RINGS.length - 1 ? VERIFIED : SIGNAL}
            emissive={i === RINGS.length - 1 ? VERIFIED : SIGNAL}
            emissiveIntensity={0.35}
            metalness={0.4}
            roughness={0.3}
          />
        </mesh>
      ))}
      <mesh ref={token}>
        <icosahedronGeometry args={[0.22, 1]} />
        <meshStandardMaterial
          ref={tokenMat}
          color={SIGNAL}
          emissive={SIGNAL}
          emissiveIntensity={0.9}
          flatShading
        />
      </mesh>
      <mesh position={[0, -2.2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[3.2, 64]} />
        <meshBasicMaterial color={MIST} transparent opacity={0.03} />
      </mesh>
    </group>
  );
}

export default function LedgerVault({ progress }: { progress: MotionValue<number> }) {
  const pointer = useRef({ x: 0, y: 0 });
  return (
    <div
      className="ledger-vault"
      aria-hidden="true"
      onPointerMove={(e) => {
        const r = e.currentTarget.getBoundingClientRect();
        pointer.current = {
          x: ((e.clientX - r.left) / r.width) * 2 - 1,
          y: ((e.clientY - r.top) / r.height) * 2 - 1,
        };
      }}
    >
      <Canvas
        dpr={[1, 1.75]}
        camera={{ position: [0, 0.6, 7.5], fov: 42 }}
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={0.4} />
        <pointLight position={[4, 5, 6]} intensity={30} color="#ffffff" />
        <Vault progress={progress} pointer={pointer} />
      </Canvas>
    </div>
  );
}
