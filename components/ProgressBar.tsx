"use client"

import { motion } from "framer-motion"
import { useStore } from "@/lib/store"

export default function ProgressBar() {
  const { progress } = useStore()

  const percentage = progress.total > 0 ? Math.min(100, (progress.current / progress.total) * 100) : 0

  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>Progress</span>
        <span>
          {progress.current} of {progress.total}
        </span>
      </div>
      <div className="h-2 bg-black/5 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5, ease: [0.4, 0, 0.2, 1] }}
          className="h-full bg-blue-600 rounded-full"
        />
      </div>
    </div>
  )
}
