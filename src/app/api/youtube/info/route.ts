// src/app/api/youtube/info/route.ts
import { NextRequest, NextResponse } from "next/server";

function getYouTubeVideoId(url: string): string | null {
  try {
    const parsed = new URL(url);

    if (parsed.hostname.includes("youtube.com")) {
      return parsed.searchParams.get("v");
    }
    if (parsed.hostname === "youtu.be") {
      return parsed.pathname.slice(1);
    }
    if (parsed.pathname.startsWith("/embed/")) {
      return parsed.pathname.split("/")[2];
    }

    return null;
  } catch {
    return null;
  }
}

export async function GET(req: NextRequest) {
  const yturl = req.nextUrl.searchParams.get("yt");
  if (!yturl) {
    return NextResponse.json({ error: "Missing yt param" }, { status: 400 });
  }

  const videoId = getYouTubeVideoId(yturl);
  if (!videoId) {
    return NextResponse.json({ error: "Invalid YouTube URL" }, { status: 400 });
  }

  try {
    const apiKey = process.env.YOUTUBE_API_KEY; // put your key in .env.local
    if (!apiKey) {
      throw new Error("Missing YOUTUBE_API_KEY in environment");
    }

    const apiUrl = `https://www.googleapis.com/youtube/v3/videos?id=${videoId}&part=snippet,contentDetails&key=${apiKey}`;
    const res = await fetch(apiUrl);
    if (!res.ok) throw new Error(await res.text());

    const data = await res.json();
    if (!data.items || !data.items[0]) {
      return NextResponse.json({ error: "Video not found" }, { status: 404 });
    }

    const item = data.items[0];
    const title = item.snippet?.title || "";
    const durationISO = item.contentDetails?.duration || "";

    // Convert ISO 8601 duration (e.g. PT4M13S) → seconds
    const match = durationISO.match(/PT(?:(\d+)M)?(?:(\d+)S)?/);
    const minutes = match?.[1] ? parseInt(match[1]) : 0;
    const seconds = match?.[2] ? parseInt(match[2]) : 0;
    const durationSeconds = minutes * 60 + seconds;

    return NextResponse.json({ title, durationSeconds });
  } catch (e: any) {
    console.error(e);
    return NextResponse.json({ error: e.message || "Failed to fetch" }, { status: 500 });
  }
}