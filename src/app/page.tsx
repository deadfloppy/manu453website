'use client'

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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
      <div className="grid grid-cols-1 md:grid-cols-2 max-w-5xl w-full rounded-2xl overflow-hidden shadow-2xl bg-black/50 backdrop-blur-xl">
        {/* Left Side - Form */}
        <motion.div 
          className="flex flex-col justify-center p-10 text-white"
          initial={{ x: -50, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <h1 className="text-3xl font-bold mb-6">Spectogram Objectificator-9000</h1>
          <p className="text-gray-300 mb-6">Upload a music file</p>
          <Button 
            className="w-full bg-white text-black hover:bg-gray-200"
            onClick={() => handleYTUpload()}>
              Select an .mp3 file
          </Button>
          <p className="text-center text-sm text-gray-400 m-6">or paste a YouTube link</p>
          <div className="flex w-full max-w-sm items-center gap-2">
            <Input
              type="link"
              placeholder="https://youtu.be/dQw4w9WgXcQ"
              value={yturl}
              onChange={(e) => setYTURL(e.target.value)}
              className="bg-gray-900 border-gray-900 text-white"
            />
            <Button type="submit" className=" bg-white text-black hover:bg-gray-200" onClick={() => handleYTUpload()}>
              View
            </Button>

          </div>


        </motion.div>

        {/* Right Side - Image */}
        <motion.div 
          className="relative hidden md:flex items-center justify-center "
          initial={{ x: 50, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <Image
            src="/retro-tv.png"
            alt="Retro TV"
            width={300}
            height={300}
            className="rounded-xl drop-shadow-2xl"
          />
        </motion.div>
      </div>
    </div>
  );
}