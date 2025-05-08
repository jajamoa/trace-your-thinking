"use client"

import { motion } from "framer-motion"
import { useStore } from "@/lib/store"

interface ElegantProgressBarProps {
  progress?: {
    current: number
    total: number
  }
  processingCount?: number
}

export default function ElegantProgressBar({ progress, processingCount }: ElegantProgressBarProps) {
  const storeProgress = useStore((state) => state.progress)
  const pendingRequests = useStore((state) => state.pendingRequests)

  // Use provided progress or fall back to store progress
  const { current, total } = progress || storeProgress
  
  // Use provided processing count or calculate from store
  const activeRequests = processingCount !== undefined ? 
    processingCount : 
    pendingRequests.filter(req => 
      req.status === 'pending' || req.status === 'processing'
    ).length

  const percentage = total > 0 ? Math.min(100, (current / total) * 100) : 0

  return (
    <div className="w-full py-4">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-light text-gray-600">Interview Progress</span>
        <div className="flex items-center">
          {activeRequests > 0 && (
            <div className="text-xs text-gray-600 mr-3 py-1 px-2 bg-[#f0eeea] rounded-full flex items-center">
              <span className="animate-pulse inline-block h-2 w-2 rounded-full bg-[#555555] mr-1"></span>
              {activeRequests === 1 
                ? "Processing 1 question" 
                : `Processing ${activeRequests} questions`}
            </div>
          )}
          <span className="text-sm font-medium">{Math.floor(percentage)}%</span>
        </div>
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
