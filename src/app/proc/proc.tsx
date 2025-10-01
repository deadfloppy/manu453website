'use client'

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import  Link  from "next/link"
import Image from "next/image";
import * as ytdl from 'ytdl-core'


export default function LinkProcessor(): TSX.Element {
    const router = useRouter();

    const [yturl, setYTURL] = useState<string>("");
    setYTURL()

    const handleYTUpload = () => {
      if (!yturl.trim()) return; // if no URL
      router.push(`/viz?yt=${encodeURIComponent(yturl)}`);
    }

    async () => {
      const data = await ytdl.getInfo(yturl);
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
        <p className="text-center font-bold mv-6 text-gray-300">Processing page</p>

        <p className="text-center mv-6 text-black-300">{data}</p>
        
        
        </motion.div>
   </div>
   
      </div>
  );
}