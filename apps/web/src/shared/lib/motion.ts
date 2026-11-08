import type { Transition, Variants } from 'motion/react'

// Movimiento del sistema: rápido (120–220 ms), suave y sin rebotes.
export const ease = [0.22, 1, 0.36, 1] as const

export const transition: Transition = { duration: 0.2, ease }

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 6 },
  show: { opacity: 1, y: 0, transition },
}

export const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.035 } },
}
