"use client"

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import { Mic } from "lucide-react"
import { useStore } from "@/lib/store"

export default function MicIndicator() {
  const { isRecording } = useStore()
  const [seconds, setSeconds] = useState(0)

  useEffect(() => {
    let interval: NodeJS.Timeout

    if (isRecording) {
      setSeconds(0)
      interval = setInterval(() => {
        setSeconds((s) => s + 1)
      }, 1000)
    } else {
      setSeconds(0)
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [isRecording])

  const formatTime = (totalSeconds: number) => {
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`
  }

  if (!isRecording) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      transition={{ duration: 0.2 }}
      className="flex items-center gap-2 p-3 bg-red-500/10 rounded-lg border border-red-500/20"
    >
      <div className="relative">
        <Mic className="h-5 w-5 text-red-500" />
        <motion.div
          animate={{ scale: [1, 1.5, 1] }}
          transition={{ repeat: Number.POSITIVE_INFINITY, duration: 1.5 }}
          className="absolute inset-0 rounded-full bg-red-500/20"
        />
      </div>
      <div className="text-sm font-medium text-red-500">
        Recording <span className="font-mono">{formatTime(seconds)}</span>
      </div>
    </motion.div>
  )
}
