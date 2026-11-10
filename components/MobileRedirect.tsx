"use client"

import Image from "next/image"
import Link from "next/link"
import { Monitor, ArrowRight } from "lucide-react"
import Footer from "./Footer"
import DreamBrand from "./DreamBrand"

export default function MobileRedirect() {
  return (
    <main className="dream-page dream-mobile">
      <DreamBrand />
      <Image src="/images/thinking-neighborhood.jpg" alt="A colorful neighborhood of people sharing ideas" width={1536} height={1024} priority className="dream-mobile-image" />
      <section className="dream-panel">
        <Monitor size={36} className="mx-auto mb-4 text-sky-700" aria-hidden="true" />
        <h1 className="text-2xl font-bold mb-3">A bigger window into your world.</h1>
        <p className="text-slate-600 leading-relaxed mb-6">This study is designed for a laptop or desktop computer. Come back on a bigger screen to start your conversation.</p>
        <Link href="/about" className="dream-button inline-flex items-center justify-center gap-2 px-6 py-3">About the study <ArrowRight size={18} aria-hidden="true" /></Link>
      </section>
      <Footer />
    </main>
  )
}
