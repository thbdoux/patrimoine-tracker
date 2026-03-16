const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

async function apiFetch<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }
  const res = await fetch(url.toString());
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

// --- Types ---

export interface Change {
  value: number;
  pct: number;
}

export interface Overview {
  total_eur: number;
  changes: {
    "1d": Change;
    "7d": Change;
    "30d": Change;
    "90d": Change;
    "1y": Change;
    inception: Change;
  };
  last_updated: string | null;
}

export interface AllocationItem {
  key: string;
  value_eur: number;
  pct: number;
}

export interface AllocationDetail {
  account_type: string;
  source: string;
  value_eur: number;
  pct: number;
}

export interface Allocation {
  total_eur: number;
  by_type: AllocationItem[];
  by_source: AllocationItem[];
  detail: AllocationDetail[];
}

export interface TimePoint {
  ts: string;
  total_eur: number;
}

export interface StackedPoint {
  ts: string;
  [accountType: string]: string | number;
}

export interface ReturnPoint {
  date: string;
  return_pct: number;
}

export interface Account {
  id: string;
  source: string;
  account_type: string;
  label: string | null;
  currency: string | null;
  institution: string | null;
  balance: number | null;
  balance_eur: number;
  price_eur: number | null;
  captured_at: string | null;
  change_1d: number | null;
  change_1d_pct: number | null;
}

export interface AccountHistoryPoint {
  ts: string;
  balance: number;
  balance_eur: number | null;
  price_eur: number | null;
}

export interface PerformanceMetrics {
  ath: number | null;
  ath_date: string | null;
  max_drawdown_pct: number | null;
  current_drawdown_pct: number | null;
  volatility_30d_annualised: number | null;
  volatility_1y_annualised: number | null;
}

export interface SyncStatus {
  source: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  accounts_synced: number;
  error_message: string | null;
}

// --- API calls ---

export type Period = "7D" | "1M" | "3M" | "6M" | "1Y" | "ALL";
export type Granularity = "1H" | "6H" | "1D" | "1W" | "1M";

export const api = {
  overview: () => apiFetch<Overview>("/overview"),
  allocation: () => apiFetch<Allocation>("/allocation"),
  history: (period: Period = "1Y", granularity: Granularity = "1D") =>
    apiFetch<TimePoint[]>("/history", { period, granularity }),
  stackedHistory: (period: Period = "1Y", granularity: Granularity = "1D") =>
    apiFetch<StackedPoint[]>("/history/stacked", { period, granularity }),
  returns: (period: Period = "1Y") =>
    apiFetch<ReturnPoint[]>("/history/returns", { period }),
  accounts: () => apiFetch<Account[]>("/accounts"),
  accountHistory: (id: string, period: Period = "3M") =>
    apiFetch<AccountHistoryPoint[]>(`/accounts/${id}/history`, { period }),
  performance: () => apiFetch<PerformanceMetrics>("/metrics/performance"),
  syncStatus: () => apiFetch<SyncStatus[]>("/metrics/sync"),
};
