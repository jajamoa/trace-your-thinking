"use client"

import { motion } from "framer-motion"
import { useStore } from "@/lib/store"

export default function ProlificIdBadge() {
  const { prolificId } = useStore()

  if (!prolificId) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="bg-[#f5f2eb] border border-[#e0ddd5] rounded-full px-3 py-1 text-xs font-mono"
    >
      ID: {prolificId}
    </motion.div>
  )
}
