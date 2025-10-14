import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";
import fs from "fs";
import { randomUUID } from "crypto";

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

export async function POST(req: NextRequest) {

  const STORAGE_PATH=`${process.cwd()}`
  //const STORAGE_PATH="/mnt/volume-nov/"

  try {
    const { yt, startSeconds, duration, mode } = await req.json();

    console.log(mode)

    if (!yt || startSeconds == null || !duration) {
      return NextResponse.json({ error: "Missing params" }, { status: 400 });
    }

    const videoId = getYouTubeVideoId(yt);
    if (!videoId) {
      return NextResponse.json({ error: "Invalid YouTube URL" }, { status: 400 });
    }

    // Create a temp folder for this job
    const jobId = randomUUID();
    const tmpDir = path.join(STORAGE_PATH, "tmp", jobId);
    fs.mkdirSync(tmpDir, { recursive: true });

    const audioPath = path.join(tmpDir, `${jobId}.wav`);

    // Download 15s audio segment using yt-dlp
    await new Promise<void>((resolve, reject) => {
      const args = [
        "-x", "--audio-format", "wav",
	      "--cookies", `${path.join(process.cwd(), "misc", "cookies.txt")}`,
        "--download-sections", `*${startSeconds}-${startSeconds + duration}`,
        "-o", audioPath,
        yt
      ];
      const proc = spawn("yt-dlp", args);

      proc.stderr.on("data", d => console.error("[yt-dlp]", d.toString()));
      proc.on("close", code => {
        if (code !== 0) return reject(new Error("yt-dlp failed"));
        // Rename to clip.mp3 (yt-dlp adds extension automatically)
        const file = fs.readdirSync(tmpDir).find(f => f.startsWith(`${jobId}`) && f.endsWith(".wav"));
        if (!file) return reject(new Error("No wav downloaded"));
        // fs.renameSync(path.join(tmpDir, file), audioPath);
        resolve();
      });
    });

    // Run Python script: assume it takes input wav, outputs STL+USDZ to tmpDir
    await new Promise<void>((resolve, reject) => {
      //const proc = spawn("python3", ["scripts/generate_model.py", jobId]);
      const proc = spawn("python3", ["-u", "./src/app/api/generate-stl/backend.py", jobId, mode]);

      proc.stdout.on("data", d => console.log("[backend]", d.toString()));
      proc.stderr.on("data", d => console.error("[backend-err]", d.toString()));

      proc.on("close", code => {
        if (code !== 0) return reject(new Error("Python script failed"));
        resolve();
      });

    });


    // Move STL + USDZ into /public/models/{jobId}
    const publicDir = path.join(process.cwd(), "public", "models");
    fs.mkdirSync(publicDir, { recursive: true });

    for (const file of fs.readdirSync(tmpDir)) {
      if (file.endsWith(".stl") || file.endsWith(".usdz")) {
        fs.renameSync(path.join(tmpDir, file), path.join(publicDir, file));
        console.log("moved!!!!!")
      }
    }

    
    // if in boombox mode, run joining script
    // if (mode === "boombox") {
    //   await new Promise<void>((resolve, reject) => {
    //     console.log("[API] Joining STLs...")
    //     const proc = spawn("python3", ["./src/app/api/generate-stl/stl_joiner.py", jobId]);
    //     proc.stdout.on("data", d => console.log("[joiner]", d.toString()));
    //     proc.stderr.on("data", d => console.error("[joiner-err]", d.toString()));

    //     const obj1 = path.join("./public/models/", `${jobId}-1.stl` )
    //     const obj2 = path.join("./public/models/", `${jobId}-2.stl`)
    //     fs.rm(obj1, { force: true }, (err) => {
    //       if (err) console.error(`Failed to remove ${obj1}:`, err);
    //     });
    //     fs.rm(obj2, { force: true }, (err) => {
    //       if (err) console.error(`Failed to remove ${obj2}:`, err);
    //     })
    //     proc.on("close", code => {
    //       if (code !== 0) return reject(new Error("Joiner script failed"));
    //       resolve();
    //     });
    //   })
    // }
    
    // convert stl for AR
    await new Promise<void>((resolve, reject) => {
      const proc = spawn("python3", ["./src/app/api/generate-stl/stl_converter.py", jobId, mode]);
      proc.stdout.on("data", d => console.log("[converter]", d.toString()));
      proc.stdout.on("data", d => console.error("[converter-err]", d.toString()));
      proc.on("close", code => {
        if (code !== 0) return reject(new Error("Converter script failed"));
        resolve();
      });
    })

    const obj1 = path.join("./public/models/", `${jobId}-1.stl` )
      const obj2 = path.join("./public/models/", `${jobId}-2.stl`)
      fs.rm(obj1, { force: true }, (err) => {
        if (err) console.error(`Failed to remove ${obj1}:`, err);
      });
      fs.rm(obj2, { force: true }, (err) => {
        if (err) console.error(`Failed to remove ${obj2}:`, err);
      })

    return NextResponse.json({
      success: true,
      vizPath: `/models/${jobId}.stl`
    });
  } catch (e) {
    console.error(e);
    return NextResponse.json({ error: (e as Error).message || "Processing failed" }, { status: 500 });
  }
}
