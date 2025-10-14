'use client'

import { use, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Slider } from "@/components/ui/slider";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import Link from "next/link";
import Image from "next/image";
import React from "react";


export default function LinkProcessor({searchParams,}: {searchParams: Promise<{yt: string}>; }): React.JSX.Element {
  const router = useRouter();
  const ytparam = use(searchParams).yt;

  const [yturl, setYTURL] = useState<string>(ytparam);
  const [title, setTitle] = useState<string>("");
  const [durationSeconds, setDurationSeconds] = useState<number | null>(null);
  const [startSeconds, setStartSeconds] = useState<number>(0);
  const [loadingInfo, setLoadingInfo] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"none" | "boombox" | "record">("none");

  useEffect(() => {
    if (!yturl) return;
    // fetch video info from server-side API route which should call YouTube Data API
    const fetchInfo = async () => {
      setLoadingInfo(true);
      setError(null);
      try {
        const res = await fetch(`/api/youtube/info?yt=${encodeURIComponent(yturl)}`);
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        // expected { title: string, durationSeconds: number }
        setTitle(data.title || "");
        setDurationSeconds(typeof data.durationSeconds === 'number' ? data.durationSeconds : null);
        setStartSeconds(0);
      } catch (e) {
        console.error(e);
        setError((e as Error).message || String(e));
      } finally {
        setLoadingInfo(false);
      }
    };
    fetchInfo();
  }, [yturl]);

  const toMMSS = (s: number) => {
    const mm = Math.floor(s / 60).toString().padStart(2, '0');
    const ss = Math.floor(s % 60).toString().padStart(2, '0');
    return `${mm}:${ss}`;
  }

  const handleProcess = async () => {
    if (!yturl) return setError('No YouTube URL');
    if (durationSeconds === null) return setError('Video duration unknown');
    // constrain startSeconds
    const maxStart = Math.max(0, durationSeconds - 15);
    const start = Math.min(Math.max(0, Math.floor(startSeconds)), maxStart);
    setProcessing(true);
    setError(null);
    try {
      const res = await fetch('/api/generate-stl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ yt: yturl, startSeconds: start, duration: 15, mode: mode })
      });
      console.log("POST request done")
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      // expected response { success: true, vizPath: string }
      // redirect to /viz with same yt param and start time
      console.log("pushing to viz")
	router.push(`/viz?pt=${encodeURIComponent(data.vizPath)}`);
    } 
	catch (e) {
      console.error(e);
      setError((e as Error).message || String(e));
    } finally {
      setProcessing(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-900 to-orange-800">
      <div className="grid grid-cols-1 md:grid-cols-1 max-w-5xl w-full rounded-2xl overflow-hidden shadow-2xl bg-black/50 backdrop-blur-xl">
        <motion.div
    className="flex flex-col md:flex-row p-10 text-white gap-8"
    initial={{ x: -50, opacity: 0 }}
    animate={{ x: 0, opacity: 1 }}
    transition={{ duration: 0.5 }}
>

  {/* Main processing area */}
  <div className="flex-1">
    <p className="text-center font-bold mv-6 text-gray-300">Processing page</p>

    {/* YouTube URL input */}
    <label className="text-sm text-gray-300">YouTube URL</label>
    <div className="flex gap-2 mt-2">
      <Input value={yturl} onChange={(e) => setYTURL(e.target.value)} placeholder="https://www.youtube.com/watch?v=..." />
      <Button onClick={() => { if (yturl.trim()) router.push(`/proc?yt=${encodeURIComponent(yturl)}`) }}>Load</Button>
    </div>

    {loadingInfo && <p className="mt-4">Loading video info...</p>}
    {error && <p className="mt-4 text-red-400">{error}</p>}

    {title && (
      <div className="mt-6">
        <p className="font-semibold">{title}</p>
        <p className="text-sm text-gray-300">Duration: {durationSeconds !== null ? toMMSS(durationSeconds) : 'unknown'}</p>

        <div className="mt-4">
          <label className="text-sm text-gray-300">Start time (seconds) — max 15s segment</label>
          <div className="mt-4">
            <Slider
              value={[startSeconds]}
              onValueChange={(value) => setStartSeconds(value[0])}
              min={0}
              max={Math.max(0, (durationSeconds || 0) - 15)}
              step={1}
              className="w-full"
            />
            <div className="flex justify-between text-sm text-gray-400 mt-2">
              <span>{toMMSS(startSeconds)}</span>
              <span>{toMMSS(Math.min((startSeconds || 0) + 15, durationSeconds || 0))}</span>
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">If you enter a start time near the end of the video, the component will clamp the segment to a 15s window or less.</p>

          <div className="mt-6">
            <Button onClick={handleProcess} disabled={processing}>{processing ? 'Processing...' : 'Download 30s & Generate 3D'}</Button>
          </div>
        </div>
      </div>
    )}
  </div>

  <div className="flex-shrink-0 w-48 flex flex-col items-center gap-4 mt-8 md:mt-0">
    {/* Image that updates with mode */}
    <div className="w-32 h-32">
      <Image
        src={
          mode === "none"
            ? "/none.png"
            : mode === "boombox"
            ? "/boombox.png"
            : "/record.png"
        }
        alt={mode}
        width={128}
        height={128}
        className="object-contain"
      />
    </div>

    {/* Toggle buttons */}
    <ToggleGroup
      type="single"
      value={mode}
      onValueChange={(val) => setMode(val as typeof mode)}
      className="flex flex-col gap-4 w-full items-center"
    >
      <ToggleGroupItem
        value="none"
        aria-label="None mode"
        className="px-6 py-3 rounded-lg border border-gray-500 text-lg text-center hover:border-white data-[state=on]:border-blue-500 w-full text-center"
      >
        None
      </ToggleGroupItem>
      <ToggleGroupItem
        value="boombox"
        aria-label="Boombox mode"
        className="px-6 py-3 rounded-lg border border-gray-500 text-lg text-center hover:border-white data-[state=on]:border-blue-500 w-full text-center"
      >
        Boombox
      </ToggleGroupItem>
      <ToggleGroupItem
        value="record"
        aria-label="Record mode"
        className="px-6 py-3 rounded-lg border border-gray-500 text-lg text-center hover:border-white data-[state=on]:border-blue-500 w-full text-center"
      >
        Record
      </ToggleGroupItem>
    </ToggleGroup>
  </div>
</motion.div>
      </div>
    </div>
  );
}
