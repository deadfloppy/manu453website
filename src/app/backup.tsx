'use client'

import { useState } from "react";
import { motion } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import Image from "next/image";


export default function SignupPage(): JSX.Element {
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [agreed, setAgreed] = useState<boolean>(false);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-900 to-orange-800">
      <div className="grid grid-cols-1 md:grid-cols-2 max-w-5xl w-full rounded-2xl overflow-hidden shadow-2xl bg-black/50 backdrop-blur-xl">
        {/* Left Side - Form */}
        <motion.div 
          className="flex flex-col justify-center p-10 text-white"
          initial={{ x: -50, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <h1 className="text-3xl font-bold mb-6">Sign up</h1>
          <p className="text-gray-300 mb-6">Create your BTR account and grow your share of the Bitcoin Treasury Reserve.</p>
          <form className="flex flex-col gap-4">
            <Input 
              type="email" 
              placeholder="Enter Email" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)}
              className="bg-gray-900/70 border-gray-700 text-white"
            />
            <Input 
              type="password" 
              placeholder="Create Password" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)}
              className="bg-gray-900/70 border-gray-700 text-white"
            />
            <div className="flex items-center gap-2">
              <Checkbox checked={agreed} onCheckedChange={(checked) => setAgreed(Boolean(checked))} />
              <span className="text-sm text-gray-300">I Agree To The Terms & Privacy Policy</span>
            </div>
            <Button className="w-full bg-white text-black hover:bg-gray-200" disabled={!agreed}>
              Create Account
            </Button>
          </form>

          <div className="my-6 text-center text-gray-400">or sign up via</div>


          <p className="text-center text-sm text-gray-400 mt-6">
            Already Have An Account? <a href="/login" className="text-red-400 hover:underline">Login</a>
          </p>
        </motion.div>

        {/* Right Side - Image */}
        <motion.div 
          className="relative hidden md:flex items-center justify-center bg-gradient-to-br from-red-700 to-orange-600"
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