import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatEur(value: number, decimals = 0): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatPct(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export function formatDateShort(iso: string): string {
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
  }).format(new Date(iso));
}

export function isPositive(value: number | null | undefined): boolean {
  return (value ?? 0) >= 0;
}

export function computeHHI(items: { pct: number }[]): number {
  return items.reduce((sum, item) => sum + Math.pow(item.pct, 2), 0);
}

/** Map account type to human-readable French label */
export const ACCOUNT_TYPE_LABELS: Record<string, string> = {
  checking: "Compte courant",
  savings: "Livret",
  loan: "Crédit",
  pea: "PEA",
  pee: "PEE",
  per: "PER",
  life_insurance: "Assurance vie",
  brokerage: "Brokerage",
  crypto_spot: "Crypto Spot",
  crypto_staking: "Crypto Staking",
  other: "Autre",
};

export const ACCOUNT_TYPE_COLORS: Record<string, string> = {
  checking: "#64748b",
  savings: "#22c55e",
  loan: "#ef4444",
  pea: "#3b82f6",
  pee: "#6366f1",
  per: "#8b5cf6",
  life_insurance: "#f59e0b",
  brokerage: "#06b6d4",
  crypto_spot: "#f97316",
  crypto_staking: "#fb923c",
  other: "#94a3b8",
};

export const SOURCE_COLORS: Record<string, string> = {
  powens: "#3b82f6",
  binance: "#f59e0b",
};
