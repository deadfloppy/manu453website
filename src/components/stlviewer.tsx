"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { useEffect, useState } from "react";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader";
import * as THREE from "three";

interface STLViewerProps {
  url: string; // URL to the STL file
}

export default function STLViewer({ url }: STLViewerProps) {
  const [geometry, setGeometry] = useState<THREE.BufferGeometry | null>(null);

  useEffect(() => {
    const loader = new STLLoader();
    loader.load(
      url,
      (geo) => {
        geo.center(); // center the model
        setGeometry(geo);
      },
      undefined,
      (err) => console.error("Error loading STL:", err)
    );
  }, [url]);

  return (
    <div className="w-full h-[600px] bg-white rounded-2xl shadow-lg">
      <Canvas camera={{ position: [0, 0, 100], fov: 50 }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 10]} intensity={1} />
        {geometry && (
          <mesh geometry={geometry} scale={[0.5, 0.5, 0.5]}>
            <meshStandardMaterial color="orange" metalness={0.3} roughness={0.6} />
          </mesh>
        )}
        <OrbitControls />
      </Canvas>
    </div>
  );
}