'use client'

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import  Link  from "next/link"
import STLViewer from "@/components/stlviewer";
import Image from "next/image";


export default function SpectogramVisualizer(): TSX.Element {
    const router = useRouter();

    const [yturl, setYTURL] = useState<string>("");

    const handleYTUpload = () => {
      if (!yturl.trim()) return; // if no URL
      router.push(`/viz?yt=${encodeURIComponent(yturl)}`);
    }

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
        <p className="text-center font-bold mv-6 text-gray-300">Viz page</p>

        <STLViewer url="/3DBenchy.stl"></STLViewer>
        
        <Button asChild
            className="w-full bg-white text-black hover:bg-gray-200 mt-6">
              <Link href="intent://arvr.google.com/scene-viewer/1.0?file=https://github.com/deadfloppy/manu453website/raw/refs/heads/main/3DBenchy.glb&mode=ar_only#Intent;scheme=https;package=com.google.ar.core;action=android.intent.action.VIEW;S.browser_fallback_url=https://developers.google.com/ar;end;">View in AR</Link>
          </Button>
        </motion.div>
   </div>
   
      </div>
  );
}