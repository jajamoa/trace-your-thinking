"use client"

import { useEffect, useRef } from "react"
import { motion } from "framer-motion"

interface ConfettiPiece {
  x: number
  y: number
  size: number
  color: string
  rotation: number
  speed: number
  oscillationSpeed: number
  angle: number
  shape: "circle" | "square" | "triangle"
  opacity: number
}

export default function Confetti() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const confettiPieces = useRef<ConfettiPiece[]>([])
  const animationFrameId = useRef<number | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // Set canvas size
    const resizeCanvas = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }

    window.addEventListener("resize", resizeCanvas)
    resizeCanvas()

    // Create confetti pieces
    // More sophisticated color palette
    const colors = [
      "#333333", // Dark gray
      "#2563EB", // Blue
      "#555555", // Gray
      "#777777", // Light gray
      "#999999", // Very light gray
    ]

    const shapes = ["circle", "square", "triangle"] as const
    const pieceCount = 200

    for (let i = 0; i < pieceCount; i++) {
      confettiPieces.current.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height - canvas.height,
        size: Math.random() * 8 + 2, // Smaller pieces for elegance
        color: colors[Math.floor(Math.random() * colors.length)],
        rotation: Math.random() * 2 * Math.PI,
        speed: Math.random() * 2 + 1, // Slower fall for elegance
        oscillationSpeed: Math.random() * 0.2 + 0.1, // Gentler oscillation
        angle: Math.random() * Math.PI * 2,
        shape: shapes[Math.floor(Math.random() * shapes.length)],
        opacity: Math.random() * 0.8 + 0.2, // Varied opacity
      })
    }

    // Animation loop
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      confettiPieces.current.forEach((piece) => {
        ctx.save()
        ctx.translate(piece.x, piece.y)
        ctx.rotate(piece.rotation)
        ctx.globalAlpha = piece.opacity

        ctx.fillStyle = piece.color

        // Draw different shapes
        if (piece.shape === "circle") {
          ctx.beginPath()
          ctx.arc(0, 0, piece.size / 2, 0, Math.PI * 2)
          ctx.fill()
        } else if (piece.shape === "square") {
          ctx.fillRect(-piece.size / 2, -piece.size / 2, piece.size, piece.size)
        } else if (piece.shape === "triangle") {
          ctx.beginPath()
          ctx.moveTo(0, -piece.size / 2)
          ctx.lineTo(piece.size / 2, piece.size / 2)
          ctx.lineTo(-piece.size / 2, piece.size / 2)
          ctx.closePath()
          ctx.fill()
        }

        ctx.restore()

        // Update position with more elegant motion
        piece.y += piece.speed
        piece.x += Math.sin(piece.angle) * 1.5
        piece.rotation += 0.005
        piece.angle += piece.oscillationSpeed / 100

        // Reset if out of bounds
        if (piece.y > canvas.height) {
          piece.y = -piece.size
          piece.x = Math.random() * canvas.width
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
      transition={{ duration: 0.5 }}
      className="fixed inset-0 pointer-events-none z-50"
      aria-hidden="true"
    />
  )
}
