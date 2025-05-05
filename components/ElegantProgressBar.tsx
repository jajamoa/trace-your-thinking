"use client"

import { motion } from "framer-motion"
import { useStore } from "@/lib/store"

interface ElegantProgressBarProps {
  progress?: {
    current: number
    total: number
  }
}

export default function ElegantProgressBar({ progress }: ElegantProgressBarProps) {
  const storeProgress = useStore((state) => state.progress)

  // Use provided progress or fall back to store progress
  const { current, total } = progress || storeProgress

  const percentage = total > 0 ? Math.min(100, (current / total) * 100) : 0

  return (
    <div className="w-full py-4">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-light text-gray-600">Interview Progress</span>
        <span className="text-sm font-medium">{Math.floor(percentage)}%</span>
      </div>

      <div className="relative">
        {/* Background track */}
        <div className="h-2 bg-[#e0ddd5] rounded-full overflow-hidden">
          {/* Progress fill */}
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${percentage}%` }}
            transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
            className="h-full bg-[#333333] rounded-full"
          />
        </div>
      </div>
    </div>
  )
}
