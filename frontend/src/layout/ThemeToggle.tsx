import { Icon } from '@/components/ui'
import { cn } from '@/lib/cn'
import { useTheme } from '@/lib/theme'

export const iconButton =
  'grid size-9 flex-none place-items-center rounded-lg border border-line bg-surface text-muted transition-colors hover:bg-surface-2 hover:text-ink'

/** Switches between the light and dark theme; the choice is remembered on this device. */
export function ThemeToggle({ className }: { className?: string }) {
  const { theme, toggle } = useTheme()
  const next = theme === 'dark' ? 'light' : 'dark'
  return (
    <button
      type="button"
      className={cn(iconButton, className)}
      title={`Switch to ${next} theme`}
      aria-label={`Switch to ${next} theme`}
      onClick={toggle}
    >
      <Icon name={theme === 'dark' ? 'sun' : 'moon'} strokeWidth={2} className="size-[17px]" />
    </button>
  )
}
