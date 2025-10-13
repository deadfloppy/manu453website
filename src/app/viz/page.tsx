'use client'

import { use, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import  Link  from "next/link"
import STLViewer from "@/components/stlviewer";
import Image from "next/image";
import React from "react";


export default function SpectogramVisualizer({searchParams,}: {searchParams: Promise<{pt: string}>; }): React.JSX.Element {
    const router = useRouter();

    const [yturl, setYTURL] = useState<string>("");
    const filepath = use(searchParams).pt;
    const [isIOS, setIsIOS] = useState(false);

    useEffect(() => {
    // Detect iOS devices
    //const iOS = /Mac/iPad|iPhone|iPod/i.test(navigator.userAgent);
    const iOS = true
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
        {/* Left Side - Form */}
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
        
	<Button asChild
            className="w-full bg-white text-black hover:bg-gray-200 mt-2">
          <a href={`${filepath}`} download>
            Download STL
          </a>
        </Button>

        </motion.div>
   </div>
   
      </div>
  );
}
