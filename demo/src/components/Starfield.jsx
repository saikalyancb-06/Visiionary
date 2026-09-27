import { useEffect, useRef } from 'react'

export default function Starfield() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animId
    let width = (canvas.width = window.innerWidth)
    let height = (canvas.height = window.innerHeight)

    const handleResize = () => {
      if (!canvas) return
      width = canvas.width = window.innerWidth
      height = canvas.height = window.innerHeight
    }
    window.addEventListener('resize', handleResize, { passive: true })

    // Generate lightweight stars
    const starCount = 140
    const stars = new Float32Array(starCount * 4) // x, y, radius, alphaSpeed
    for (let i = 0; i < starCount; i++) {
      const idx = i * 4
      stars[idx] = Math.random() * width
      stars[idx + 1] = Math.random() * height
      stars[idx + 2] = Math.random() * 1.5 + 0.5 // radius
      stars[idx + 3] = Math.random() * 0.02 + 0.005 // pulse speed
    }

    let t = 0
    const render = () => {
      t += 0.03
      ctx.clearRect(0, 0, width, height)
      ctx.fillStyle = '#ffffff'

      for (let i = 0; i < starCount; i++) {
        const idx = i * 4
        const x = stars[idx]
        const y = stars[idx + 1]
        const r = stars[idx + 2]
        const sp = stars[idx + 3]
        const alpha = 0.2 + 0.5 * Math.abs(Math.sin(t * sp * 10 + i))

        ctx.globalAlpha = alpha
        ctx.beginPath()
        ctx.arc(x, y, r, 0, Math.PI * 2)
        ctx.fill()
      }

      animId = requestAnimationFrame(render)
    }

    render()

    return () => {
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animId)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-0"
      style={{ opacity: 0.85 }}
    />
  )
}
