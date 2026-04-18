export function nowIso(): string {
  return new Date().toISOString();
}

export function addHours(hours: number, base = new Date()): string {
  const clone = new Date(base);
  clone.setHours(clone.getHours() + hours);
  return clone.toISOString();
}

export function addDays(days: number, base = new Date()): string {
  const clone = new Date(base);
  clone.setDate(clone.getDate() + days);
  return clone.toISOString();
}

export function toDateOnlyIso(value: string): string {
  return new Date(value).toISOString().slice(0, 10);
}
