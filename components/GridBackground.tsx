"use client"

import { useEffect, useRef } from "react"
import { motion } from "framer-motion"

export default function GridBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationFrameId = useRef<number | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // Initialize grid lines array first
    const gridLines: {
      start: { x: number; y: number }
      end: { x: number; y: number }
      width: number
      color: string
      progress: number
      speed: number
    }[] = []

    // Set canvas size
    const resizeCanvas = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight

      // Clear existing grid lines
      gridLines.length = 0

      // Generate new grid lines
      drawGrid()
    }

    // Function to draw grid
    const drawGrid = () => {
      const width = canvas.width
      const height = canvas.height

      // Horizontal lines
      const horizontalCount = Math.floor(height / 40)
      for (let i = 0; i <= horizontalCount; i++) {
        const y = i * 40
        const speed = 0.002 + Math.random() * 0.003
        const initialProgress = Math.random()

        gridLines.push({
          start: { x: 0, y },
          end: { x: width, y },
          width: Math.random() < 0.1 ? 0.8 : 0.4,
          color: `rgba(0, 0, 0, ${0.03 + Math.random() * 0.03})`,
          progress: initialProgress,
          speed,
        })
      }

      // Vertical lines
      const verticalCount = Math.floor(width / 40)
      for (let i = 0; i <= verticalCount; i++) {
        const x = i * 40
        const speed = 0.002 + Math.random() * 0.003
        const initialProgress = Math.random()

        gridLines.push({
          start: { x, y: 0 },
          end: { x, y: height },
          width: Math.random() < 0.1 ? 0.8 : 0.4,
          color: `rgba(0, 0, 0, ${0.03 + Math.random() * 0.03})`,
          progress: initialProgress,
          speed,
        })
      }

      // Add some diagonal lines for visual interest
      for (let i = 0; i < 15; i++) {
        const startX = Math.random() * width
        const startY = Math.random() * height
        const endX = startX + (Math.random() - 0.5) * width
        const endY = startY + (Math.random() - 0.5) * height
        const speed = 0.001 + Math.random() * 0.002
        const initialProgress = Math.random()

        gridLines.push({
          start: { x: startX, y: startY },
          end: { x: endX, y: endY },
          width: 0.3,
          color: `rgba(0, 0, 0, ${0.02 + Math.random() * 0.02})`,
          progress: initialProgress,
          speed,
        })
      }
    }

    window.addEventListener("resize", resizeCanvas)
    resizeCanvas()

    // Animation loop
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Draw and animate grid lines
      gridLines.forEach((line) => {
        // Update progress
        line.progress += line.speed
        if (line.progress > 1) line.progress = 0

        // Calculate current end point based on progress
        const currentEndX = line.start.x + (line.end.x - line.start.x) * line.progress
        const currentEndY = line.start.y + (line.end.y - line.start.y) * line.progress

        // Draw line
        ctx.beginPath()
        ctx.moveTo(line.start.x, line.start.y)
        ctx.lineTo(currentEndX, currentEndY)
        ctx.strokeStyle = line.color
        ctx.lineWidth = line.width
        ctx.stroke()
      })

      animationFrameId.current = requestAnimationFrame(animate)
    }

    animate()

    // Cleanup
    return () => {
      if (animationFrameId.current) {
        cancelAnimationFrame(animationFrameId.current)
      }
      window.removeEventListener("resize", resizeCanvas)
    }
  }, [])

  return (
    <motion.canvas
      ref={canvasRef}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 1 }}
      className="fixed inset-0 pointer-events-none z-0"
      aria-hidden="true"
    />
  )
}
