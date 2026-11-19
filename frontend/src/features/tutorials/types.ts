import type { Role } from '@/auth/types'
import type { IconName } from '@/components/ui'

/** A numbered mark on a screenshot. Position and size are percentages of the image. */
export type Mark = {
  x: number
  y: number
  w: number
  h: number
  /** What the mark points at, shown in the numbered legend beside the image. */
  label: string
  /** Corner for the number badge (default top-right, where labels and text rarely are). */
  badge?: 'tl' | 'tr' | 'bl' | 'br'
}

export type TutorialStep = {
  title: string
  /** Who does this step (the account to sign in with). */
  role: Role
  /** The page to try it on, if it has one. */
  path?: string
  image: string
  /** Pixel size of the screenshot, so the frame keeps its shape while it loads. */
  size: [width: number, height: number]
  alt: string
  body: string
  marks: Mark[]
  tip?: string
}

export type SampleFile = { label: string; file: string; description: string }

export type Tutorial = {
  /** URL slug: /system/tutorials/<id> */
  id: string
  feature: 'F1' | 'F2' | 'F3' | 'F4' | 'F5'
  title: string
  summary: string
  icon: IconName
  roles: Role[]
  /** The values typed in during the walkthrough, so anyone can repeat it. */
  sample: { label: string; value: string }[]
  files: SampleFile[]
  steps: TutorialStep[]
}
