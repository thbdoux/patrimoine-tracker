import { useQuery as useTanstackQuery } from "@tanstack/react-query";
import { api, type Period, type Granularity } from "@/lib/api";

export function useOverview() {
  return useTanstackQuery({
    queryKey: ["overview"],
    queryFn: api.overview,
    refetchInterval: 60_000,
  });
}

export function useAllocation() {
  return useTanstackQuery({
    queryKey: ["allocation"],
    queryFn: api.allocation,
    refetchInterval: 60_000,
  });
}

export function useHistory(period: Period, granularity: Granularity) {
  return useTanstackQuery({
    queryKey: ["history", period, granularity],
    queryFn: () => api.history(period, granularity),
    refetchInterval: 300_000,
  });
}

export function useStackedHistory(period: Period, granularity: Granularity) {
  return useTanstackQuery({
    queryKey: ["stackedHistory", period, granularity],
    queryFn: () => api.stackedHistory(period, granularity),
    refetchInterval: 300_000,
  });
}

export function useReturns(period: Period) {
  return useTanstackQuery({
    queryKey: ["returns", period],
    queryFn: () => api.returns(period),
    refetchInterval: 300_000,
  });
}

export function useAccounts() {
  return useTanstackQuery({
    queryKey: ["accounts"],
    queryFn: api.accounts,
    refetchInterval: 60_000,
  });
}

export function useAccountHistory(id: string, period: Period) {
  return useTanstackQuery({
    queryKey: ["accountHistory", id, period],
    queryFn: () => api.accountHistory(id, period),
    enabled: !!id,
    refetchInterval: 300_000,
  });
}

export function usePerformance() {
  return useTanstackQuery({
    queryKey: ["performance"],
    queryFn: api.performance,
    refetchInterval: 300_000,
  });
}

export function useSyncStatus() {
  return useTanstackQuery({
    queryKey: ["syncStatus"],
    queryFn: api.syncStatus,
    refetchInterval: 30_000,
  });
}
