"use client"

import { motion } from "framer-motion"
import Transcript from "@/components/Transcript"
import MicIndicator from "@/components/MicIndicator"
import ProgressBar from "@/components/ProgressBar"

export default function Sidebar() {
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className="w-72 border-l border-[#333333] bg-[#1f1f1f] h-screen flex flex-col"
    >
      <div className="p-4 border-b border-[#333333]">
        <h2 className="text-lg font-light tracking-wide">Interview Session</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <Transcript />
      </div>

      <div className="p-4 border-t border-[#333333] space-y-4">
        <MicIndicator />
        <ProgressBar />
      </div>
    </motion.div>
  )
}
