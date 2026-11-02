import { Icon } from '@/components/ui'

export function Brand() {
  return (
    <span className="flex items-center gap-2.5">
      <span className="grid size-8 flex-none place-items-center rounded-lg bg-accent text-on-accent shadow-card">
        <Icon name="verify" strokeWidth={2} className="size-[18px]" />
      </span>
      <span className="leading-tight">
        <b className="block text-[15px] font-semibold tracking-[-0.01em]">CRVR</b>
        <span className="hidden text-xs text-faint min-[480px]:block">Carbon Removal Registry</span>
      </span>
    </span>
  )
}
