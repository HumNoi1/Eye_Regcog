"use client";

// Install deps first:
//   npm i onnxruntime-web
// Put your ONNX model in a **public** Hugging Face repo and set HF_REPO + MODEL_FILE below.
// This page uses getUserMedia + onnxruntime-web to run YOLO fully in the browser.

import { useEffect, useRef, useState } from "react";
import * as ort from "onnxruntime-web";

// ================== CONFIG ==================
const HF_REPO = "HumNoi1/eye-detect-yolo"; // <-- change
const MODEL_FILE = "yolo11n.onnx"; // e.g. best.onnx / model.onnx
const MODEL_SIZE = 640; // YOLO input size (square)
const CONF_THRES = 0.7;
const IOU_THRES = 0.45;
const CLASS_NAMES = ["eye"]; // <-- change to your classes if multiple
// ============================================

export default function FaceDetectionPage() {
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [cameraStatus, setCameraStatus] = useState<
    "ready" | "starting" | "active" | "error"
  >("ready");
  const [modelStatus, setModelStatus] = useState<
    "idle" | "loading" | "loaded" | "error"
  >("idle");

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rafRef = useRef<number | null>(null);
  const sessionRef = useRef<ort.InferenceSession | null>(null);

  // Load model once
  useEffect(() => {
    (async () => {
      try {
        setModelStatus("loading");
        // Prefer WebGPU if available, fallback to WebGL/wasm
        const epOrder: ort.InferenceSession.ExecutionProviderName[] = (await (ort as any).env.webgpu?.isSupported)
          ? ["webgpu", "wasm"]
          : ["webgl", "wasm"];

        const modelUrl = `https://huggingface.co/${HF_REPO}/resolve/main/${MODEL_FILE}`;

        const session = await ort.InferenceSession.create(modelUrl, {
          executionProviders: epOrder,
          graphOptimizationLevel: "all",
        });
        sessionRef.current = session;
        setModelStatus("loaded");
      } catch (e) {
        console.error("Failed to load ONNX:", e);
        setModelStatus("error");
      }
    })();
    return () => {
      stopCamera();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Camera controls
  const startCamera = async () => {
    try {
      setCameraStatus("starting");
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setIsCameraOn(true);
      setCameraStatus("active");
      loop();
    } catch (err) {
      console.error("getUserMedia error", err);
      setCameraStatus("error");
      setIsCameraOn(false);
    }
  };

  const stopCamera = () => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (videoRef.current && videoRef.current.srcObject) {
      (videoRef.current.srcObject as MediaStream)
        .getTracks()
        .forEach((t) => t.stop());
      videoRef.current.srcObject = null;
    }
    setIsCameraOn(false);
    setCameraStatus("ready");
    // Clear canvas
    const ctx = canvasRef.current?.getContext("2d");
    if (ctx && canvasRef.current) ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
  };

  const handleCameraToggle = () => {
    if (!isCameraOn) startCamera();
    else stopCamera();
  };

  // Main loop
  const loop = async () => {
    const tick = async () => {
      if (!videoRef.current || !canvasRef.current || !sessionRef.current) {
        rafRef.current = requestAnimationFrame(tick);
        return;
      }
      const v = videoRef.current;
      const c = canvasRef.current;
      const ctx = c.getContext("2d");
      if (!ctx) {
        rafRef.current = requestAnimationFrame(tick);
        return;
      }

      // Fit canvas to video
      if (c.width !== v.videoWidth || c.height !== v.videoHeight) {
        c.width = v.videoWidth;
        c.height = v.videoHeight;
      }

      // Draw frame to an offscreen canvas for resizing
      const off = new OffscreenCanvas(MODEL_SIZE, MODEL_SIZE);
      const octx = off.getContext("2d");
      if (!octx) return;
      // Letterbox to square
      const scale = Math.min(MODEL_SIZE / v.videoWidth, MODEL_SIZE / v.videoHeight);
      const nw = v.videoWidth * scale;
      const nh = v.videoHeight * scale;
      const dx = (MODEL_SIZE - nw) / 2;
      const dy = (MODEL_SIZE - nh) / 2;
      octx.fillStyle = "black";
      octx.fillRect(0, 0, MODEL_SIZE, MODEL_SIZE);
      octx.drawImage(v, 0, 0, v.videoWidth, v.videoHeight, dx, dy, nw, nh);

      // Get image data and normalize to 0..1, CHW
      const img = octx.getImageData(0, 0, MODEL_SIZE, MODEL_SIZE);
      const chw = new Float32Array(3 * MODEL_SIZE * MODEL_SIZE);
      for (let i = 0, p = 0; i < img.data.length; i += 4) {
        const r = img.data[i] / 255;
        const g = img.data[i + 1] / 255;
        const b = img.data[i + 2] / 255;
        chw[p] = r; // R
        chw[p + MODEL_SIZE * MODEL_SIZE] = g; // G
        chw[p + 2 * MODEL_SIZE * MODEL_SIZE] = b; // B
        p++;
      }

      const input = new ort.Tensor("float32", chw, [1, 3, MODEL_SIZE, MODEL_SIZE]);
      let output: Record<string, ort.Tensor>;
      try {
        output = (await sessionRef.current.run({ images: input })) as any; // common YOLO input name: images
      } catch {
        // Try generic key if model uses different input name
        const feeds: any = {};
        const names = sessionRef.current.inputNames;
        feeds[names[0]] = input;
        output = (await sessionRef.current.run(feeds)) as any;
      }

      const outName = Object.keys(output)[0];
      const out = output[outName].data as Float32Array; // shape [1, N, 85] or [N, 85]
      const [boxes, scores, labels] = decodeYOLO(out, MODEL_SIZE, MODEL_SIZE, v.videoWidth, v.videoHeight, dx, dy, scale);
      const keep = nms(boxes, scores, IOU_THRES).filter((i) => scores[i] >= CONF_THRES);

      // render
      ctx.drawImage(v, 0, 0);
      ctx.lineWidth = 2;
      ctx.font = "14px ui-sans-serif, system-ui, -apple-system";
      keep.forEach((i) => {
        const [x1, y1, x2, y2] = boxes[i];
        const w = x2 - x1;
        const h = y2 - y1;
        ctx.strokeStyle = "#22c55e";
        ctx.fillStyle = "#22c55e";
        ctx.strokeRect(x1, y1, w, h);
        const label = CLASS_NAMES[labels[i]] ?? `id:${labels[i]}`;
        const txt = `${label} ${(scores[i] * 100).toFixed(1)}%`;
        const tw = ctx.measureText(txt).width + 8;
        ctx.fillRect(x1, Math.max(0, y1 - 18), tw, 18);
        ctx.fillStyle = "#0a0a0a";
        ctx.fillText(txt, x1 + 4, Math.max(12, y1 - 6));
      });

      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
  };

  return (
    <div className="relative min-h-dvh overflow-hidden">
      {/* Background: gradient + blobs */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-[radial-gradient(1200px_600px_at_20%_-10%,rgba(59,130,246,0.25),transparent),radial-gradient(900px_500px_at_100%_20%,rgba(16,185,129,0.2),transparent),linear-gradient(to_bottom,var(--color-background),var(--color-background))]" />
        <div className="absolute -left-24 top-24 size-[360px] rounded-full blur-3xl opacity-30 bg-gradient-to-tr from-blue-500 to-cyan-400" />
        <div className="absolute right-0 -bottom-24 size-[420px] rounded-full blur-3xl opacity-25 bg-gradient-to-tr from-emerald-500 to-teal-400" />
        <div className="absolute right-16 top-16 hidden sm:block">
          <Sparkles />
        </div>
      </div>

      <main className="mx-auto grid min-h-dvh w-full max-w-6xl grid-cols-1 lg:grid-cols-2">
        {/* Left: marketing / brand */}
        <section className="order-2 lg:order-1 hidden lg:flex flex-col justify-center p-10">
          <a
            href="/login"
            className="group inline-flex w-fit items-center gap-2 rounded-full border border-black/10 px-3 py-1 text-sm opacity-80 transition hover:bg-black/[.04] dark:border-white/20 dark:hover:bg-white/[.06]"
          >
            <span aria-hidden>←</span> Back to Login
          </a>

          <div className="mt-10">
            <h1 className="text-4xl/tight font-semibold">Camera + On-device YOLO</h1>
            <p className="mt-4 text-lg opacity-80">
              รันโมเดลจาก Hugging Face (ONNX) บนเบราว์เซอร์ โดยไม่ต้องมี backend
            </p>
            <div className="mt-8 grid gap-4">
              <div className="flex items-center gap-3">
                <div className="size-2 rounded-full bg-green-500" />
                <span className="text-sm opacity-70">เรียลไทม์ด้วย WebGPU/WebGL/WASM</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="size-2 rounded-full bg-blue-500" />
                <span className="text-sm opacity-70">โมเดลโหลดจาก Hugging Face Hub</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="size-2 rounded-full bg-purple-500" />
                <span className="text-sm opacity-70">ไม่มีการส่งภาพขึ้นเซิร์ฟเวอร์</span>
              </div>
            </div>
          </div>
        </section>

        {/* Right: camera card */}
        <section className="order-1 lg:order-2 grid place-items-center p-6 lg:p-10">
          <div className="w-full max-w-md">
            <div className="rounded-2xl border border-black/10 bg-white/70 p-6 shadow-xl backdrop-blur-md dark:border-white/15 dark:bg-black/30">
              {/* Title */}
              <div className="mb-4 text-center">
                <h2 className="text-2xl font-semibold">Camera Preview</h2>
                <p className="mt-1 text-sm opacity-80">เปิดกล้องและตรวจจับด้วย YOLO (ONNX)</p>
              </div>

              {/* Camera & Canvas */}
              <div className="relative mx-auto h-64 w-full overflow-hidden rounded-xl border-2 border-dashed border-black/20 bg-black/5 dark:border-white/20 dark:bg-white/5">
                <video ref={videoRef} className="h-full w-full object-cover" muted playsInline />
                <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />
                {(!isCameraOn || modelStatus !== "loaded") && (
                  <div className="absolute inset-0 grid place-items-center text-sm opacity-80">
                    {!isCameraOn ? (
                      <span>กดปุ่มด้านล่างเพื่อเปิดกล้อง</span>
                    ) : modelStatus === "loading" ? (
                      <span>กำลังโหลดโมเดลจาก Hugging Face…</span>
                    ) : modelStatus === "error" ? (
                      <span>โหลดโมเดลไม่สำเร็จ</span>
                    ) : null}
                  </div>
                )}
              </div>

              {/* Status badges */}
              <div className="mt-3 grid grid-cols-2 gap-2 text-center text-xs">
                <Badge label="Camera" status={cameraStatus} />
                <Badge label="Model" status={modelStatus === "loaded" ? "active" : modelStatus === "loading" ? "starting" : modelStatus === "error" ? "error" : "ready"} />
              </div>

              {/* Controls */}
              <div className="mt-4 grid gap-3">
                <button
                  onClick={handleCameraToggle}
                  disabled={modelStatus === "loading" || modelStatus === "error"}
                  className={`h-11 w-full rounded-xl font-medium transition ${
                    !isCameraOn
                      ? "bg-foreground text-background hover:opacity-90 active:opacity-80"
                      : "bg-red-500 text-white hover:bg-red-600 active:bg-red-700"
                  }`}
                >
                  {!isCameraOn ? "เปิดกล้อง" : "ปิดกล้อง"}
                </button>
              </div>

              {/* Tips */}
              <div className="mt-6 text-xs opacity-70">
                <p className="mb-2 font-medium">คำแนะนำ:</p>
                <ul className="space-y-1 list-disc pl-4">
                  <li>ตั้งค่า <code>HF_REPO</code> และ <code>MODEL_FILE</code> ให้ตรงกับรีโปโมเดลของคุณ</li>
                  <li>ทำรีโปโมเดลเป็น <b>public</b> เพื่อดึงได้จากเบราว์เซอร์ (อย่าใส่ token ใน client)</li>
                  <li>แนะนำไฟล์ ONNX ส่งออกที่ขนาดอินพุต 640x640 แบบ YOLOv5/8</li>
                </ul>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function Badge({ label, status }: { label: string; status: "ready" | "starting" | "active" | "error" }) {
  return (
    <div className="inline-flex items-center justify-center gap-2 rounded-full px-3 py-1 border border-black/10 dark:border-white/15">
      <div
        className={`size-2 rounded-full ${
          status === "ready"
            ? "bg-gray-400"
            : status === "starting"
            ? "bg-yellow-400 animate-pulse"
            : status === "active"
            ? "bg-green-400"
            : "bg-red-400"
        }`}
      />
      <span className="capitalize text-xs">{label}: {status}</span>
    </div>
  );
}

function Sparkles() {
  return (
    <svg width="140" height="140" viewBox="0 0 140 140" fill="none" aria-hidden className="opacity-50">
      <g filter="url(#f1)">
        <path d="M70 10 L75 35 L100 40 L75 45 L70 70 L65 45 L40 40 L65 35 Z" fill="url(#g1)" />
      </g>
      <g filter="url(#f2)">
        <circle cx="110" cy="28" r="6" fill="url(#g2)" />
      </g>
      <defs>
        <linearGradient id="g1" x1="40" y1="10" x2="100" y2="70" gradientUnits="userSpaceOnUse">
          <stop stopColor="#60A5FA" />
          <stop offset="1" stopColor="#34D399" />
        </linearGradient>
        <linearGradient id="g2" x1="104" y1="22" x2="116" y2="34" gradientUnits="userSpaceOnUse">
          <stop stopColor="#34D399" />
          <stop offset="1" stopColor="#60A5FA" />
        </linearGradient>
        <filter id="f1" x="30" y="0" width="80" height="90" filterUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
          <feGaussianBlur in="SourceGraphic" stdDeviation="0.8" />
        </filter>
        <filter id="f2" x="100" y="18" width="20" height="20" filterUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
          <feGaussianBlur in="SourceGraphic" stdDeviation="0.6" />
        </filter>
      </defs>
    </svg>
  );
}

// ================== YOLO Helpers ==================
function decodeYOLO(
  raw: Float32Array,
  inW: number,
  inH: number,
  vidW: number,
  vidH: number,
  dx: number,
  dy: number,
  scale: number
): [number[][], number[], number[]] {
  // Try to infer shape: either [N,85] or [1,N,85]
  const stride = 5 + CLASS_NAMES.length; // [cx,cy,w,h,obj, ...classes]
  const N = Math.floor(raw.length / stride);
  const boxes: number[][] = [];
  const scores: number[] = [];
  const labels: number[] = [];

  for (let i = 0; i < N; i++) {
    const off = i * stride;
    const cx = raw[off + 0];
    const cy = raw[off + 1];
    const w = raw[off + 2];
    const h = raw[off + 3];
    const obj = raw[off + 4];

    // class probs
    let best = 0;
    let bestScore = 0;
    for (let c = 0; c < CLASS_NAMES.length; c++) {
      const s = raw[off + 5 + c];
      if (s > bestScore) {
        bestScore = s;
        best = c;
      }
    }
    const score = obj * bestScore;
    if (score < 0.001) continue;

    // Convert xywh (model space) -> xyxy (video space)
    const x = (cx - w / 2 - dx) / scale;
    const y = (cy - h / 2 - dy) / scale;
    const x2 = (cx + w / 2 - dx) / scale;
    const y2 = (cy + h / 2 - dy) / scale;

    boxes.push([clamp(x, 0, vidW), clamp(y, 0, vidH), clamp(x2, 0, vidW), clamp(y2, 0, vidH)]);
    scores.push(score);
    labels.push(best);
  }
  return [boxes, scores, labels];
}

function nms(boxes: number[][], scores: number[], iouThr: number): number[] {
  const idxs = scores
    .map((s, i) => [s, i] as const)
    .sort((a, b) => b[0] - a[0])
    .map(([, i]) => i);
  const keep: number[] = [];
  while (idxs.length) {
    const i = idxs.shift()!;
    keep.push(i);
    for (let j = idxs.length - 1; j >= 0; j--) {
      const o = iou(boxes[i], boxes[idxs[j]]);
      if (o > iouThr) idxs.splice(j, 1);
    }
  }
  return keep;
}

function iou(a: number[], b: number[]) {
  const x1 = Math.max(a[0], b[0]);
  const y1 = Math.max(a[1], b[1]);
  const x2 = Math.min(a[2], b[2]);
  const y2 = Math.min(a[3], b[3]);
  const inter = Math.max(0, x2 - x1) * Math.max(0, y2 - y1);
  const areaA = (a[2] - a[0]) * (a[3] - a[1]);
  const areaB = (b[2] - b[0]) * (b[3] - b[1]);
  return inter / Math.max(1e-6, areaA + areaB - inter);
}

function clamp(x: number, a: number, b: number) {
  return Math.max(a, Math.min(b, x));
}
