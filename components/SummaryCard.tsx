"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { Clock, Network, Shapes } from "lucide-react"

export default function SummaryCard() {
  const [graphUrl, setGraphUrl] = useState<string>("")

  useEffect(() => {
    // Fetch the mock graph SVG
    fetch("/api/mockGraph.svg")
      .then((response) => {
        if (response.ok) {
          return response.text()
        }
        throw new Error("Failed to load graph")
      })
      .then((svgText) => {
        // Create a data URL from the SVG
        const dataUrl = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgText)}`
        setGraphUrl(dataUrl)
      })
      .catch((error) => {
        console.error("Error loading graph:", error)
      })
  }, [])

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className="bg-surface backdrop-blur-md rounded-3xl p-8 shadow-sm border border-white/5"
    >
      <h2 className="text-xl font-light mb-6 tracking-wide">Interview Summary</h2>

      <div className="space-y-6">
        <div className="grid grid-cols-[auto_1fr] gap-x-4 items-center">
          <Clock className="h-5 w-5 text-white/70" />
          <div>
            <div className="text-sm text-gray-400 mb-1">Duration</div>
            <div className="font-light text-lg">15m 42s</div>
          </div>
        </div>

        <div className="grid grid-cols-[auto_1fr] gap-x-4 items-center">
          <Network className="h-5 w-5 text-white/70" />
          <div>
            <div className="text-sm text-gray-400 mb-1">Node Count</div>
            <div className="font-light text-lg">24</div>
          </div>
        </div>

        <div className="grid grid-cols-[auto_1fr] gap-x-4 items-center">
          <Shapes className="h-5 w-5 text-white/70" />
          <div>
            <div className="text-sm text-gray-400 mb-1">Motif Count</div>
            <div className="font-light text-lg">3</div>
          </div>
        </div>
      </div>

      {graphUrl && (
        <div className="mt-8">
          <div className="text-sm text-gray-400 mb-2">Graph Preview</div>
          <div className="rounded-lg overflow-hidden border border-white/10">
            <img src={graphUrl || "/placeholder.svg"} alt="Interview graph visualization" className="w-full h-auto" />
          </div>
        </div>
      )}
    </motion.div>
  )
}
