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
  try {
    const { yt, startSeconds, duration } = await req.json();

    if (!yt || startSeconds == null || !duration) {
      return NextResponse.json({ error: "Missing params" }, { status: 400 });
    }

    const videoId = getYouTubeVideoId(yt);
    if (!videoId) {
      return NextResponse.json({ error: "Invalid YouTube URL" }, { status: 400 });
    }

    // Create a temp folder for this job
    const jobId = randomUUID();
    const tmpDir = path.join(process.cwd(), "tmp", jobId);
    fs.mkdirSync(tmpDir, { recursive: true });

    const audioPath = path.join(tmpDir, `${jobId}.wav`);

    // Download 15s audio segment using yt-dlp
    await new Promise<void>((resolve, reject) => {
      const args = [
        "-x", "--audio-format", "wav",
        "--download-sections", `*${startSeconds}-${startSeconds + duration}`,
        "-o", path.join(tmpDir, `${jobId}.wav`),
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
      const pythonCommand = process.platform === "win32" ? "python" : "python3";
      const proc = spawn(pythonCommand, ["./src/app/api/generate-stl/backend.py", jobId]);

      proc.stdout.on("data", d => console.log("[python]", d.toString()));
      proc.stderr.on("data", d => console.error("[python-err]", d.toString()));

      proc.on("close", code => {
        if (code !== 0) return reject(new Error("Python script failed"));
        resolve();
      });

    });

    await new Promise(resolve => setTimeout(resolve, 1000));

    const stlPath = path.join(tmpDir, `${jobId}.stl`);

    console.log("Checking for STL at:", stlPath);
    console.log("STL exists?", fs.existsSync(stlPath));

    if (!fs.existsSync(stlPath)) {
      console.error("STL file not found, checking directory contents:");
      console.log(fs.readdirSync(tmpDir));
      throw new Error("STL file not created");
    }

    // Convert STL to GLB and USDZ
    
    await new Promise<void>((resolve, reject) => {
      const pythonCommand = process.platform === "win32" ? "python" : "python3";
      const convertScript = path.join(process.cwd(), "stl_converter.py");
      const proc = spawn(pythonCommand, [convertScript, stlPath]);

      proc.stdout.on("data", d => console.log("[convert]", d.toString()));
      proc.stderr.on("data", d => console.error("[convert-err]", d.toString()));

      proc.on("close", code => {
        if (code !== 0) {
          console.warn("Conversion failed, continuing with STL only");
        }
        resolve(); // Don't reject - STL viewer still works
      });
    });

    // Move STL, GLB, and USDZ into /public/models/
    const publicDir = path.join(process.cwd(), "public", "models");
    fs.mkdirSync(publicDir, { recursive: true });

    for (const file of fs.readdirSync(tmpDir)) {
      if (file.endsWith(".stl") || file.endsWith(".usdz") || file.endsWith(".glb")) {
        fs.renameSync(path.join(tmpDir, file), path.join(publicDir, file));
        console.log(`Moved: ${file}`);
      }
    }

    // Clean up temp directory
    fs.rmSync(tmpDir, { recursive: true, force: true });

    return NextResponse.json({
      success: true,
      vizPath: `/models/${jobId}.stl`,
      glbPath: `/models/${jobId}.glb`,
      usdzPath: `/models/${jobId}.usdz`
    });

  } catch (e: any) {
    console.error(e);
    return NextResponse.json({ error: e.message || "Processing failed" }, { status: 500 });
  }
}