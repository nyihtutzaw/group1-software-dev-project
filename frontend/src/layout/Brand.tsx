import { Icon } from '@/components/ui'

export function Brand() {
  return (
    <span className="flex items-center gap-2.5">
      <span className="grid size-8 flex-none place-items-center rounded-[9px] bg-accent text-white">
        <Icon name="verify" strokeWidth={2} className="size-[18px]" />
      </span>
      <span>
        <b className="block font-serif text-[17px] leading-tight">CRVR</b>
        <span className="block font-mono text-[10.5px] tracking-[0.1em] text-faint">REGISTRY</span>
      </span>
    </span>
  )
}
