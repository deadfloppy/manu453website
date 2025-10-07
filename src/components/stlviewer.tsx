"use client";

import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { useEffect, useState } from "react";
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader';
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
      geo.center();
      geo.computeVertexNormals();
      geo.normalizeNormals();
      setGeometry(geo);
    },
    undefined,
  (err) => console.error("Error loading STL:", err)
);
  }, [url]);

  return (
    <div className="w-full h-[600px] bg-white rounded-2xl shadow-lg">
      <Canvas camera={{ position: [0, 0, 100], fov: 50 }}>
        <ambientLight intensity={0.2} />
        <directionalLight position={[5, 5, 10]} intensity={0.8} />
        <pointLight position={[0, 0, 50]} intensity={1} />
        {geometry && (
          <mesh geometry={geometry} scale={[0.5, 0.5, 0.5]}>
          <meshStandardMaterial
            color="orange"
            metalness={0}
            roughness={1}
            side={THREE.DoubleSide}      // render only front faces
            depthWrite={true}           // ensure depth buffer is written
            depthTest={true}            // ensure correct occlusion
            transparent={false}         // disable transparency entirely
          />          </mesh>
        )}
        <OrbitControls />
      </Canvas>
    </div>
  );
}