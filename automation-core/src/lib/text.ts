export function compactText(value: string | null | undefined, limit = 280): string {
  const cleaned = (value ?? "").replace(/\s+/g, " ").trim();
  if (!cleaned) {
    return "";
  }
  if (cleaned.length <= limit) {
    return cleaned;
  }
  return `${cleaned.slice(0, limit - 1).trimEnd()}…`;
}

export function parseDisplayName(value: string): { name: string; email: string } {
  const match = value.match(/^(.*?)(?:<([^>]+)>)?$/);
  if (!match) {
    return { name: value.trim(), email: value.trim().toLowerCase() };
  }
  const name = match[1]?.replace(/(^"|"$)/g, "").trim() ?? "";
  const email = (match[2] ?? match[1] ?? "").trim().toLowerCase();
  return { name: name || email, email };
}

export function unique<T>(values: T[]): T[] {
  return [...new Set(values)];
}
