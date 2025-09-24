"use client";

import { useEffect, useRef, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type CameraStatus = "ready" | "starting" | "active" | "error";

export default function FaceDetectionPage() {
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [cameraStatus, setCameraStatus] = useState<CameraStatus>("ready");
  const [processedImage, setProcessedImage] = useState<string | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const processingRef = useRef(false);

  useEffect(() => {
    if (isCameraOn) {
      void startCamera();
    } else {
      stopCamera();
    }

    return () => {
      stopCamera();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isCameraOn]);

  const startCamera = async () => {
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setLastError("เบราว์เซอร์ไม่รองรับการเปิดกล้อง");
      setCameraStatus("error");
      setIsCameraOn(false);
      return;
    }

    try {
      setCameraStatus("starting");
      setLastError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user" },
        audio: false,
      });
      streamRef.current = stream;
      const video = videoRef.current;
      if (video) {
        video.srcObject = stream;
        await video.play().catch(() => undefined);
      }
      setProcessedImage(null);
      setCameraStatus("active");
      startProcessingLoop();
    } catch (error) {
      console.error("Failed to access camera:", error);
      setLastError("ไม่สามารถเข้าถึงกล้องได้");
      setCameraStatus("error");
      stopCamera();
      setIsCameraOn(false);
    }
  };

  const stopCamera = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    processingRef.current = false;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    const video = videoRef.current;
    if (video) {
      video.pause();
      video.srcObject = null;
    }
    setProcessedImage(null);
  };

  const startProcessingLoop = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    void captureAndSendFrame();
    intervalRef.current = setInterval(() => {
      void captureAndSendFrame();
    }, 500);
  };

  const captureAndSendFrame = async () => {
    if (processingRef.current || !videoRef.current) {
      return;
    }

    const video = videoRef.current;
    if (!video.videoWidth || !video.videoHeight) {
      return;
    }

    if (!canvasRef.current) {
      canvasRef.current = document.createElement("canvas");
    }
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const context = canvas.getContext("2d");
    if (!context) {
      return;
    }
    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.8),
    );

    if (!blob) {
      return;
    }

    processingRef.current = true;

    try {
      const formData = new FormData();
      formData.append("file", blob, "frame.jpg");
      const response = await fetch(`${API_BASE_URL}/process_frame`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const data = await response.json();
      if (data?.processed_image) {
        setProcessedImage(`data:image/jpeg;base64,${data.processed_image}`);
      }
    } catch (error) {
      console.error("Failed to process frame:", error);
      setLastError("เกิดข้อผิดพลาดระหว่างส่งภาพไปยังเซิร์ฟเวอร์");
      setCameraStatus("error");
      stopCamera();
      setIsCameraOn(false);
    } finally {
      processingRef.current = false;
    }
  };

  const handleCameraToggle = () => {
    if (isCameraOn) {
      setCameraStatus("ready");
      setLastError(null);
      setIsCameraOn(false);
    } else {
      setLastError(null);
      setCameraStatus("starting");
      setIsCameraOn(true);
    }
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
            <h1 className="text-4xl/tight font-semibold">
              Camera Preview 📷
            </h1>
            <p className="mt-4 text-lg opacity-80">
              ระบบกล้องแบบเรียลไทม์ สำหรับการแสดงผลวิดีโอจากกล้องหน้า
            </p>
            <div className="mt-8 grid gap-4">
              <div className="flex items-center gap-3">
                <div className="size-2 rounded-full bg-green-500" />
                <span className="text-sm opacity-70">แสดงผลแบบเรียลไทม์</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="size-2 rounded-full bg-blue-500" />
                <span className="text-sm opacity-70">รองรับกล้องหน้า</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="size-2 rounded-full bg-purple-500" />
                <span className="text-sm opacity-70">คุณภาพ HD</span>
              </div>
            </div>
          </div>
        </section>

        {/* Right: camera card */}
        <section className="order-1 lg:order-2 grid place-items-center p-6 lg:p-10">
          <div className="w-full max-w-md">
            <div className="rounded-2xl border border-black/10 bg-white/70 p-6 shadow-xl backdrop-blur-md dark:border-white/15 dark:bg-black/30">
              {/* Logo / Title */}
              <div className="mb-6 text-center">
                <div className="mx-auto mb-3 grid size-12 place-items-center rounded-xl border border-black/10 bg-gradient-to-br from-indigo-500 to-sky-500 text-white shadow-md dark:border-white/15">
                  <span className="text-lg">📷</span>
                </div>
                <h2 className="text-2xl font-semibold">Camera Preview</h2>
                <p className="mt-1 text-sm opacity-80">
                  เปิดกล้องเพื่อดูภาพแบบเรียลไทม์
                </p>
              </div>

              {/* Camera Section */}
              <div className="mb-6">
                <div className="relative mx-auto h-64 w-full overflow-hidden rounded-xl border-2 border-dashed border-black/20 bg-black/5 dark:border-white/20 dark:bg-white/5">
                  {!isCameraOn ? (
                    <div className="flex h-full items-center justify-center">
                      <div className="text-center">
                        <div className="mx-auto mb-3 flex size-16 items-center justify-center rounded-full bg-black/10 dark:bg-white/10">
                          <span className="text-2xl">📷</span>
                        </div>
                        <p className="text-sm opacity-70">กดปุ่มด้านล่างเพื่อเปิดกล้อง</p>
                      </div>
                    </div>
                  ) : (
                    <>
                      {processedImage ? (
                        <img
                          src={processedImage}
                          alt="Processed camera frame"
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <div className="flex h-full items-center justify-center">
                          <div className="text-center">
                            <div className="mx-auto mb-3 flex size-16 items-center justify-center rounded-full bg-black/10 dark:bg-white/10">
                              <span className="text-2xl">⌛</span>
                            </div>
                            <p className="text-sm opacity-70">กำลังประมวลผลเฟรมแรก...</p>
                          </div>
                        </div>
                      )}

                      <video
                        ref={videoRef}
                        className="absolute bottom-3 right-3 h-24 w-32 rounded-lg border border-white/40 bg-black/60 object-cover shadow-lg"
                        muted
                        playsInline
                        autoPlay
                      />
                    </>
                  )}
                </div>
              </div>

              {/* Status Display */}
              <div className="mb-4 text-center">
                <div className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm border border-black/10 dark:border-white/15">
                  <div className={`size-2 rounded-full ${
                    cameraStatus === "ready" ? "bg-gray-400" :
                    cameraStatus === "starting" ? "bg-yellow-400 animate-pulse" :
                    cameraStatus === "active" ? "bg-green-400" :
                    cameraStatus === "error" ? "bg-red-400" : "bg-gray-400"
                  }`} />
                  <span className="capitalize">
                    {cameraStatus === "ready" ? "พร้อมใช้งาน" :
                     cameraStatus === "starting" ? "กำลังเริ่ม..." :
                     cameraStatus === "active" ? "กล้องเปิดอยู่" :
                     cameraStatus === "error" ? "เกิดข้อผิดพลาด" : "พร้อมใช้งาน"}
                  </span>
                </div>
                {lastError && (
                  <p className="mt-2 text-sm text-red-500">{lastError}</p>
                )}
              </div>

              {/* Control Buttons */}
              <div className="grid gap-3">
                <button
                  onClick={handleCameraToggle}
                  className={`h-11 w-full rounded-xl font-medium transition ${
                    !isCameraOn 
                      ? "bg-foreground text-background hover:opacity-90 active:opacity-80"
                      : "bg-red-500 text-white hover:bg-red-600 active:bg-red-700"
                  }`}
                >
                  {!isCameraOn ? "เปิดกล้อง" : "ปิดกล้อง"}
                </button>
              </div>

              {/* Instructions */}
              <div className="mt-6 text-xs opacity-70">
                <p className="mb-2 font-medium">คำแนะนำ:</p>
                <ul className="space-y-1">
                  <li>• อนุญาตให้เข้าถึงกล้องเมื่อเบราว์เซอร์ขอสิทธิ์</li>
                  <li>• ตรวจสอบให้แน่ใจว่ากล้องไม่ถูกใช้งานโดยแอปอื่น</li>
                  <li>• ให้แสงสว่างเพียงพอสำหรับภาพที่ชัดเจน</li>
                </ul>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function Sparkles() {
  return (
    <svg
      width="140"
      height="140"
      viewBox="0 0 140 140"
      fill="none"
      aria-hidden
      className="opacity-50"
    >
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