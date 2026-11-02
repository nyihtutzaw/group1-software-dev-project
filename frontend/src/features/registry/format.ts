export function date(value: string) {
  return new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeZone: 'UTC' }).format(
    new Date(value),
  )
}
