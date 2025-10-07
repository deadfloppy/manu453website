'use client'

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import Link from "next/link";
import STLViewer from "@/components/stlviewer";
import Image from "next/image";

export default function SpectogramVisualizer(): TSX.Element {
  const router = useRouter();
  const searchParams = useSearchParams();
  const filepath = searchParams?.get("pt") || "";

  const [isIOS, setIsIOS] = useState(false);

  useEffect(() => {
    // Detect iOS devices
    const iOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    setIsIOS(iOS);
  }, []);

  const handleARView = () => {
    if (isIOS) {
      // iOS: Use USDZ for AR Quick Look
      const usdzPath = filepath.replace('.stl', '.usdz');
      window.location.href = usdzPath;
    } else {
      // Android: Use GLB for Scene Viewer
      const glbPath = filepath.replace('.stl', '.glb');
      const fullUrl = `${window.location.origin}${glbPath}`;
      const sceneViewerUrl = `intent://arvr.google.com/scene-viewer/1.0?file=${encodeURIComponent(fullUrl)}&mode=ar_only#Intent;scheme=https;package=com.google.ar.core;action=android.intent.action.VIEW;S.browser_fallback_url=https://developers.google.com/ar;end;`;
      window.location.href = sceneViewerUrl;
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-900 to-orange-800">
      <div className="grid grid-cols-1 md:grid-cols-1 max-w-5xl w-full rounded-2xl overflow-hidden shadow-2xl bg-black/50 backdrop-blur-xl">
        <motion.div
          className="flex flex-col justify-center p-10 text-white"
          initial={{ x: -50, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <p className="text-center font-bold mv-6 text-gray-300">3D Visualization</p>

          <STLViewer url={filepath} />
          
          {filepath && (
            <Button 
              onClick={handleARView}
              className="w-full bg-white text-black hover:bg-gray-200 mt-6"
            >
              View in AR {isIOS ? '(iOS)' : '(Android)'}
            </Button>
          )}

        </motion.div>
      </div>
    </div>
  );
}