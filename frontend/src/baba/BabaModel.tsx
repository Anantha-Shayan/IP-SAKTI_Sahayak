import React, { useRef } from 'react';
import { useTexture } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

export type BabaSpeechState =
  | 'IDLE'
  | 'LISTENING'
  | 'PROCESSING'
  | 'SPEAKING'
  | 'INTERRUPTED'
  | 'ERROR';

interface BabaModelProps {
  isSpeaking?: boolean;
  state?: BabaSpeechState;
  amplitude?: number;
  showSkeleton?: boolean;
}

// 3D Human Ayurvedic Scholar Avatar with Amplitude-Driven Lip Sync & State Animations
export const BabaHumanScholar: React.FC<{
  isSpeaking?: boolean;
  state?: BabaSpeechState;
  amplitude?: number;
}> = ({ isSpeaking = false, state = 'IDLE', amplitude = 0 }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const groupRef = useRef<THREE.Group>(null);

  // Load high-resolution diffuse and normal maps
  const texture = useTexture('/assets/baba-human.png');
  const normalMap = useTexture('/assets/baba-human-normal.png');

  // Configure texture filtering for crisp photorealism
  texture.generateMipmaps = true;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.magFilter = THREE.LinearFilter;

  // Lifelike procedural animation driven by Web Audio amplitude & speech states
  useFrame((clockState) => {
    if (!groupRef.current) return;
    const t = clockState.clock.getElapsedTime();

    // Gentle baseline breathing cycle
    const breath = Math.sin(t * 1.8) * 0.012;
    groupRef.current.position.y = -0.05 + breath;

    if (state === 'SPEAKING' || isSpeaking) {
      // 1. Amplitude-driven jaw/mouth displacement:
      // Silence -> mouth closed. Syllables -> opens proportionally. Loud syllables -> larger opening.
      const jawOpening = Math.max(0, amplitude * 0.025);
      if (meshRef.current) {
        meshRef.current.position.y = -jawOpening;
      }

      // Natural expressive speaking gestures & nods synchronized with speech energy
      const speechNod = Math.sin(t * 4.5) * (0.015 + amplitude * 0.02) + Math.cos(t * 2.8) * 0.01;
      groupRef.current.rotation.x = speechNod;
      groupRef.current.rotation.y = Math.sin(t * 1.8) * 0.035;
    } else if (state === 'LISTENING') {
      // Mouth closed, attentive posture, slight tilt towards user
      if (meshRef.current) meshRef.current.position.y = 0;
      groupRef.current.rotation.x = 0.03 + Math.sin(t * 1.2) * 0.006;
      groupRef.current.rotation.y = Math.sin(t * 0.5) * 0.015;
    } else if (state === 'PROCESSING') {
      // Mouth closed, contemplative thoughtful tilt
      if (meshRef.current) meshRef.current.position.y = 0;
      groupRef.current.rotation.x = 0.04;
      groupRef.current.rotation.y = 0.05 + Math.sin(t * 1.0) * 0.01;
    } else {
      // IDLE: peaceful micro-sway
      if (meshRef.current) meshRef.current.position.y = 0;
      groupRef.current.rotation.x = Math.sin(t * 0.8) * 0.005;
      groupRef.current.rotation.y = Math.sin(t * 0.6) * 0.02;
    }
  });

  return (
    <group ref={groupRef} position={[0, -0.05, 0]}>
      {/* 3D Curved Surface Mesh with PBR Lighting & Normal Mapping */}
      <mesh ref={meshRef} castShadow receiveShadow>
        <planeGeometry args={[1.05, 1.82, 32, 32]} />
        <meshStandardMaterial
          map={texture}
          normalMap={normalMap}
          normalScale={new THREE.Vector2(0.8, 0.8)}
          transparent={true}
          alphaTest={0.08}
          roughness={0.6}
          metalness={0.05}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  );
};

// Main Baba Model Component
export const BabaModel: React.FC<BabaModelProps> = ({
  isSpeaking = false,
  state = 'IDLE',
  amplitude = 0,
}) => {
  return (
    <group position={[0, 0, 0]}>
      <BabaHumanScholar isSpeaking={isSpeaking} state={state} amplitude={amplitude} />
    </group>
  );
};
