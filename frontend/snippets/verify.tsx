'use client'
import { useEffect, useRef, useState } from 'react'
import { supabase } from './supabaseClient'

export default function FaceVerify() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [status, setStatus] = useState('ready')

  useEffect(() => {
    (async () => {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
    })()
    return () => (videoRef.current?.srcObject as MediaStream)?.getTracks().forEach(t => t.stop())
  }, [])

  const snapAndVerify = async () => {
    const canvas = document.createElement('canvas')
    const v = videoRef.current!
    canvas.width = v.videoWidth
    canvas.height = v.videoHeight
    const ctx = canvas.getContext('2d')!
    ctx.drawImage(v, 0, 0)
    const blob: Blob = await new Promise(res => canvas.toBlob(b => res(b!), 'image/jpeg', 0.92))

    const { data: { session } } = await supabase.auth.getSession()
    if (!session?.access_token) { alert('กรุณาเข้าสู่ระบบ'); return }

    const form = new FormData()
    form.append('image', blob, 'frame.jpg')

    setStatus('verifying...')
    const r = await fetch(process.env.NEXT_PUBLIC_FACE_API_BASE + '/face/verify', {
      method: 'POST',
      headers: { Authorization: `Bearer ${session.access_token}` },
      body: form
    })
    const j = await r.json()
    setStatus(j.ok ? `✅ pass (score=${j.score?.toFixed(3)})` : `❌ fail (score=${j.score?.toFixed(3)})`)
  }

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold">Face Verify</h1>
      <video ref={videoRef} className="rounded-xl w-full max-w-md" />
      <button onClick={snapAndVerify} className="px-4 py-2 rounded bg-black text-white">Verify</button>
      <div>{status}</div>
    </div>
  )
}
