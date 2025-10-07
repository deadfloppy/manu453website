'use client'

import { use, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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
        body: JSON.stringify({ yt: yturl, startSeconds: start, duration: 15 })
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      // expected response { success: true, vizPath: string }
      // redirect to /viz with same yt param and start time
      router.push(`/viz?pt=${encodeURIComponent(data.vizPath)}`);
    } catch (e) {
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
          className="flex flex-col justify-center p-10 text-white"
          initial={{ x: -50, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <p className="text-center font-bold mv-6 text-gray-300">Processing page</p>

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
                <div className="flex gap-2 mt-2 items-center">
                  <Input type="number" value={startSeconds} onChange={(e) => setStartSeconds(Number(e.target.value))} min={0} max={Math.max(0, (durationSeconds || 0) - 1)} />
                  <div className="text-sm">{toMMSS(startSeconds)} → {toMMSS(Math.min((startSeconds || 0) + 15, durationSeconds || 0))}</div>
                </div>
                <p className="text-xs text-gray-400 mt-2">If you enter a start time near the end of the video, the component will clamp the segment to a 15s window or less.</p>

                <div className="mt-6">
                  <Button onClick={handleProcess} disabled={processing}>{processing ? 'Processing...' : 'Download 15s & Generate 3D'}</Button>
                </div>
              </div>
            </div>
          )}

        </motion.div>
      </div>
    </div>
  );
}