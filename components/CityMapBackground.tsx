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
}

interface Building {
  x: number
  y: number
  width: number
  height: number
  color: string
  opacity: number
}

export default function CityMapBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationFrameId = useRef<number | null>(null)
  const roadsRef = useRef<Road[]>([])
  const buildingsRef = useRef<Building[]>([])
  const gridSizeRef = useRef(80)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // Set canvas size
    const resizeCanvas = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight

      // Regenerate the city map when resizing
      generateCityMap()
    }

    window.addEventListener("resize", resizeCanvas)
    resizeCanvas()

    // Generate city map
    function generateCityMap() {
      const gridSize = gridSizeRef.current
      const cols = Math.ceil(canvas.width / gridSize)
      const rows = Math.ceil(canvas.height / gridSize)

      // Clear existing roads and buildings
      roadsRef.current = []
      buildingsRef.current = []

      // Generate main roads (grid)
      for (let i = 0; i <= cols; i++) {
        if (Math.random() < 0.8) {
          // 80% chance to create a vertical road
          roadsRef.current.push({
            start: { x: i * gridSize, y: 0 },
            end: { x: i * gridSize, y: canvas.height },
            width: Math.random() < 0.2 ? 2 : 1, // 20% chance for wider roads
            color: "rgba(255, 255, 255, 0.1)",
            progress: 0,
            speed: 0.002 + Math.random() * 0.003,
          })
        }
      }

      for (let i = 0; i <= rows; i++) {
        if (Math.random() < 0.8) {
          // 80% chance to create a horizontal road
          roadsRef.current.push({
            start: { x: 0, y: i * gridSize },
            end: { x: canvas.width, y: i * gridSize },
            width: Math.random() < 0.2 ? 2 : 1, // 20% chance for wider roads
            color: "rgba(255, 255, 255, 0.1)",
            progress: 0,
            speed: 0.002 + Math.random() * 0.003,
          })
        }
      }

      // Generate diagonal roads
      const diagonalCount = Math.floor(Math.min(cols, rows) / 3)
      for (let i = 0; i < diagonalCount; i++) {
        const startX = Math.random() * canvas.width
        const startY = Math.random() * canvas.height
        const angle = Math.random() * Math.PI * 2
        const length = gridSize * (2 + Math.floor(Math.random() * 5))

        roadsRef.current.push({
          start: { x: startX, y: startY },
          end: {
            x: startX + Math.cos(angle) * length,
            y: startY + Math.sin(angle) * length,
          },
          width: 1,
          color: "rgba(255, 255, 255, 0.08)",
          progress: 0,
          speed: 0.003 + Math.random() * 0.004,
        })
      }

      // Generate curved roads
      const curvedCount = Math.floor(Math.min(cols, rows) / 4)
      for (let i = 0; i < curvedCount; i++) {
        const startX = Math.random() * canvas.width
        const startY = Math.random() * canvas.height
        const endX = startX + (Math.random() - 0.5) * gridSize * 4
        const endY = startY + (Math.random() - 0.5) * gridSize * 4

        roadsRef.current.push({
          start: { x: startX, y: startY },
          end: { x: endX, y: endY },
          width: 1,
          color: "rgba(255, 255, 255, 0.05)",
          progress: 0,
          speed: 0.002 + Math.random() * 0.003,
        })
      }

      // Generate buildings
      for (let i = 0; i < cols; i++) {
        for (let j = 0; j < rows; j++) {
          if (Math.random() < 0.3) {
            // 30% chance to create a building
            const x = i * gridSize + gridSize * 0.2
            const y = j * gridSize + gridSize * 0.2
            const width = gridSize * (0.3 + Math.random() * 0.3)
            const height = gridSize * (0.3 + Math.random() * 0.3)

            buildingsRef.current.push({
              x,
              y,
              width,
              height,
              color: Math.random() < 0.1 ? "rgba(37, 99, 235, 0.1)" : "rgba(255, 255, 255, 0.03)",
              opacity: 0.03 + Math.random() * 0.05,
            })
          }
        }
      }
    }

    // Animation loop
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Draw buildings
      buildingsRef.current.forEach((building) => {
        ctx.fillStyle = building.color
        ctx.globalAlpha = building.opacity
        ctx.fillRect(building.x, building.y, building.width, building.height)
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

        // Draw endpoint dot
        if (road.progress === 1 && Math.random() < 0.3) {
          ctx.beginPath()
          ctx.arc(currentEndX, currentEndY, 1, 0, Math.PI * 2)
          ctx.fillStyle = "rgba(255, 255, 255, 0.2)"
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
