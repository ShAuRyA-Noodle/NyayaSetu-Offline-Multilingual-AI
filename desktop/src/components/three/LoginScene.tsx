import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, AdaptiveDpr } from '@react-three/drei';
import * as THREE from 'three';

const FloatingShape: React.FC<{
  position: [number, number, number];
  color: string;
  speed?: number;
  size?: number;
  type?: 'icosahedron' | 'octahedron' | 'dodecahedron';
}> = ({ position, color, speed = 1, size = 1, type = 'icosahedron' }) => {
  const meshRef = useRef<THREE.Mesh>(null!);

  useFrame((_, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.x += delta * 0.15 * speed;
      meshRef.current.rotation.y += delta * 0.2 * speed;
    }
  });

  const geometry = useMemo(() => {
    switch (type) {
      case 'octahedron': return <octahedronGeometry args={[size, 0]} />;
      case 'dodecahedron': return <dodecahedronGeometry args={[size, 0]} />;
      default: return <icosahedronGeometry args={[size, 0]} />;
    }
  }, [type, size]);

  return (
    <Float speed={speed} rotationIntensity={0.4} floatIntensity={0.6}>
      <mesh ref={meshRef} position={position}>
        {geometry}
        <meshStandardMaterial
          color={color}
          transparent
          opacity={0.15}
          wireframe
          side={THREE.DoubleSide}
        />
      </mesh>
    </Float>
  );
};

const Particles: React.FC = () => {
  const pointsRef = useRef<THREE.Points>(null!);

  const particles = useMemo(() => {
    const count = 150;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const saffron = new THREE.Color('#FF9933');
    const gold = new THREE.Color('#D4A017');
    const green = new THREE.Color('#138808');

    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 20;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 20;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 15;

      const colorChoice = Math.random();
      const c = colorChoice < 0.4 ? saffron : colorChoice < 0.7 ? gold : green;
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
    }
    return { positions, colors };
  }, []);

  useFrame((_, delta) => {
    if (pointsRef.current) {
      pointsRef.current.rotation.y += delta * 0.02;
      pointsRef.current.rotation.x += delta * 0.01;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[particles.positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[particles.colors, 3]} />
      </bufferGeometry>
      <pointsMaterial size={0.06} vertexColors transparent opacity={0.6} sizeAttenuation />
    </points>
  );
};

const Scene: React.FC = () => (
  <>
    <ambientLight intensity={0.4} />
    <pointLight position={[-5, 5, 5]} intensity={0.8} color="#FF9933" />
    <pointLight position={[5, -3, 3]} intensity={0.4} color="#138808" />

    <FloatingShape position={[-3.5, 2, -2]} color="#FF9933" speed={0.8} size={1.2} type="icosahedron" />
    <FloatingShape position={[3, -1.5, -3]} color="#138808" speed={0.6} size={1} type="octahedron" />
    <FloatingShape position={[-1, -2.5, -1]} color="#D4A017" speed={1} size={0.8} type="dodecahedron" />
    <FloatingShape position={[2.5, 2.5, -4]} color="#FF9933" speed={0.7} size={0.6} type="octahedron" />
    <FloatingShape position={[-2, 0.5, -5]} color="#138808" speed={0.5} size={1.4} type="dodecahedron" />
    <FloatingShape position={[4, 0, -2]} color="#D4A017" speed={0.9} size={0.7} type="icosahedron" />

    <Particles />
  </>
);

const LoginScene: React.FC = () => (
  <div className="absolute inset-0 z-0">
    <Canvas
      camera={{ position: [0, 0, 6], fov: 60, near: 0.1, far: 100 }}
      style={{ background: 'transparent' }}
      dpr={[1, 1.5]}
    >
      <AdaptiveDpr pixelated />
      <Scene />
    </Canvas>
  </div>
);

export default LoginScene;
