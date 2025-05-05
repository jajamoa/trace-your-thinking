"use client"

import { motion } from "framer-motion"

export default function MITLogo({ className = "" }: { className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className={`${className}`}
    >
      <svg width="120" height="60" viewBox="0 0 120 60" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M0 0H12V48H0V0Z" fill="#333333" />
        <path d="M20 0H32V48H20V0Z" fill="#333333" />
        <path d="M40 0H52V48H40V0Z" fill="#333333" />
        <path d="M60 0H72V20H92V0H104V48H92V32H72V48H60V0Z" fill="#333333" />
        <path d="M112 0H120V48H112V0Z" fill="#333333" />
      </svg>
    </motion.div>
  )
}
