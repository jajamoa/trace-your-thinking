"use client"

import { useEffect, useRef } from "react"
import { motion } from "framer-motion"

interface Point {
  x: number
  y: number
}

interface Road {
  start: Point
  end: Point
  width: number
  color: string
  progress: number
  speed: number
  isMainRoad?: boolean
}

interface Landmark {
  x: number
  y: number
  radius: number
  color: string
  opacity: number
  name?: string
}

export default function SanFranciscoMap() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationFrameId = useRef<number | null>(null)
  const roadsRef = useRef<Road[]>([])
  const landmarksRef = useRef<Landmark[]>([])
  const waterRef = useRef<{ points: Point[] }>({ points: [] })

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // Set canvas size
    const resizeCanvas = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight

      // Regenerate the map when resizing
      generateSanFranciscoMap()
    }

    window.addEventListener("resize", resizeCanvas)
    resizeCanvas()

    // Generate San Francisco map
    function generateSanFranciscoMap() {
      // Clear existing elements
      roadsRef.current = []
      landmarksRef.current = []

      const width = canvas.width
      const height = canvas.height
      const centerX = width / 2
      const centerY = height / 2
      const scale = Math.min(width, height) * 0.8

      // Create the bay area outline (simplified)
      waterRef.current.points = [
        { x: centerX - scale * 0.3, y: centerY - scale * 0.4 },
        { x: centerX - scale * 0.4, y: centerY - scale * 0.2 },
        { x: centerX - scale * 0.3, y: centerY },
        { x: centerX - scale * 0.2, y: centerY + scale * 0.3 },
        { x: centerX, y: centerY + scale * 0.4 },
        { x: centerX + scale * 0.3, y: centerY + scale * 0.3 },
        { x: centerX + scale * 0.4, y: centerY },
        { x: centerX + scale * 0.3, y: centerY - scale * 0.3 },
      ]

      // Main streets - Market Street
      roadsRef.current.push({
        start: { x: centerX - scale * 0.3, y: centerY - scale * 0.1 },
        end: { x: centerX + scale * 0.3, y: centerY + scale * 0.2 },
        width: 1.5,
        color: "rgba(0, 0, 0, 0.7)",
        progress: 0,
        speed: 0.004,
        isMainRoad: true,
      })

      // Embarcadero
      roadsRef.current.push({
        start: { x: centerX - scale * 0.2, y: centerY - scale * 0.3 },
        end: { x: centerX + scale * 0.2, y: centerY + scale * 0.3 },
        width: 1.5,
        color: "rgba(0, 0, 0, 0.7)",
        progress: 0,
        speed: 0.003,
        isMainRoad: true,
      })

      // Golden Gate Bridge
      roadsRef.current.push({
        start: { x: centerX - scale * 0.25, y: centerY - scale * 0.35 },
        end: { x: centerX - scale * 0.35, y: centerY - scale * 0.45 },
        width: 2,
        color: "rgba(0, 0, 0, 0.8)",
        progress: 0,
        speed: 0.005,
        isMainRoad: true,
      })

      // Bay Bridge
      roadsRef.current.push({
        start: { x: centerX, y: centerY },
        end: { x: centerX + scale * 0.4, y: centerY },
        width: 2,
        color: "rgba(0, 0, 0, 0.8)",
        progress: 0,
        speed: 0.005,
        isMainRoad: true,
      })

      // Generate grid streets for downtown
      const gridSize = scale * 0.03
      const gridCenterX = centerX
      const gridCenterY = centerY - scale * 0.1
      const gridWidth = scale * 0.4
      const gridHeight = scale * 0.4

      // Horizontal streets
      for (let i = 0; i <= Math.floor(gridHeight / gridSize); i++) {
        const y = gridCenterY - gridHeight / 2 + i * gridSize
        roadsRef.current.push({
          start: { x: gridCenterX - gridWidth / 2, y },
          end: { x: gridCenterX + gridWidth / 2, y },
          width: 0.5,
          color: "rgba(0, 0, 0, 0.3)",
          progress: 0,
          speed: 0.006 + Math.random() * 0.004,
        })
      }

      // Vertical streets
      for (let i = 0; i <= Math.floor(gridWidth / gridSize); i++) {
        const x = gridCenterX - gridWidth / 2 + i * gridSize
        roadsRef.current.push({
          start: { x, y: gridCenterY - gridHeight / 2 },
          end: { x, y: gridCenterY + gridHeight / 2 },
          width: 0.5,
          color: "rgba(0, 0, 0, 0.3)",
          progress: 0,
          speed: 0.006 + Math.random() * 0.004,
        })
      }

      // Add diagonal streets for neighborhoods like Mission, Castro, etc.
      for (let i = 0; i < 8; i++) {
        const startX = gridCenterX + (Math.random() - 0.5) * scale * 0.6
        const startY = gridCenterY + (Math.random() - 0.5) * scale * 0.6
        const angle = Math.random() * Math.PI * 2
        const length = gridSize * (3 + Math.floor(Math.random() * 8))

        roadsRef.current.push({
          start: { x: startX, y: startY },
          end: {
            x: startX + Math.cos(angle) * length,
            y: startY + Math.sin(angle) * length,
          },
          width: 0.5,
          color: "rgba(0, 0, 0, 0.25)",
          progress: 0,
          speed: 0.004 + Math.random() * 0.003,
        })
      }

      // Add landmarks
      // Golden Gate Park
      landmarksRef.current.push({
        x: centerX - scale * 0.15,
        y: centerY - scale * 0.2,
        radius: scale * 0.05,
        color: "rgba(0, 0, 0, 0.1)",
        opacity: 0.1,
        name: "Golden Gate Park",
      })

      // Coit Tower
      landmarksRef.current.push({
        x: centerX,
        y: centerY - scale * 0.15,
        radius: scale * 0.01,
        color: "rgba(0, 0, 0, 0.6)",
        opacity: 0.6,
        name: "Coit Tower",
      })

      // Salesforce Tower
      landmarksRef.current.push({
        x: centerX + scale * 0.05,
        y: centerY,
        radius: scale * 0.015,
        color: "rgba(0, 0, 0, 0.7)",
        opacity: 0.7,
        name: "Salesforce Tower",
      })

      // Add more subtle neighborhood indicators
      for (let i = 0; i < 15; i++) {
        landmarksRef.current.push({
          x: centerX + (Math.random() - 0.5) * scale * 0.6,
          y: centerY + (Math.random() - 0.5) * scale * 0.6,
          radius: scale * 0.005 * Math.random(),
          color: "rgba(0, 0, 0, 0.15)",
          opacity: 0.1 + Math.random() * 0.1,
        })
      }
    }

    // Animation loop
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Draw water (bay area)
      ctx.beginPath()
      if (waterRef.current.points.length > 0) {
        ctx.moveTo(waterRef.current.points[0].x, waterRef.current.points[0].y)
        for (let i = 1; i < waterRef.current.points.length; i++) {
          ctx.lineTo(waterRef.current.points[i].x, waterRef.current.points[i].y)
        }
        ctx.closePath()
        ctx.fillStyle = "rgba(0, 0, 0, 0.02)"
        ctx.fill()
      }

      // Draw landmarks
      landmarksRef.current.forEach((landmark) => {
        ctx.beginPath()
        ctx.arc(landmark.x, landmark.y, landmark.radius, 0, Math.PI * 2)
        ctx.fillStyle = landmark.color
        ctx.globalAlpha = landmark.opacity
        ctx.fill()
      })

      // Draw and animate roads
      ctx.globalAlpha = 1
      roadsRef.current.forEach((road) => {
        // Update progress
        road.progress += road.speed
        if (road.progress > 1) road.progress = 1

        // Calculate current end point based on progress
        const currentEndX = road.start.x + (road.end.x - road.start.x) * road.progress
        const currentEndY = road.start.y + (road.end.y - road.start.y) * road.progress

        // Draw road
        ctx.beginPath()
        ctx.moveTo(road.start.x, road.start.y)
        ctx.lineTo(currentEndX, currentEndY)
        ctx.strokeStyle = road.color
        ctx.lineWidth = road.width
        ctx.stroke()

        // Draw endpoint dot for main roads
        if (road.progress === 1 && road.isMainRoad) {
          ctx.beginPath()
          ctx.arc(currentEndX, currentEndY, 1.5, 0, Math.PI * 2)
          ctx.fillStyle = "rgba(0, 0, 0, 0.5)"
          ctx.fill()
        }
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
