import type {
  HasTimeseriesResponse,
  HarnessPendingResponse,
  ScanResponse,
} from './types';

const BASE =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const API_KEY =
  process.env.NEXT_PUBLIC_API_KEY ?? 'dev-key-insecure';

function authHeaders(): HeadersInit {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${API_KEY}`,
  };
}

export async function fetchHasTimeseries(
  agentId: string,
  fromTs?: string,
  toTs?: string,
): Promise<HasTimeseriesResponse> {
  const params = new URLSearchParams();
  if (fromTs) params.set('from_ts', fromTs);
  if (toTs) params.set('to_ts', toTs);
  const qs = params.size ? `?${params.toString()}` : '';
  const res = await fetch(`${BASE}/v1/agents/${agentId}/has${qs}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`HAS fetch failed: ${res.status}`);
  return res.json() as Promise<HasTimeseriesResponse>;
}

export async function fetchHarnessPending(
  agentId: string,
): Promise<HarnessPendingResponse> {
  const res = await fetch(`${BASE}/v1/agents/${agentId}/harness/pending`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`Harness fetch failed: ${res.status}`);
  return res.json() as Promise<HarnessPendingResponse>;
}

export async function approveHarnessRule(
  ruleId: string,
  approved: boolean,
): Promise<{ rule_id: string; status: string }> {
  const res = await fetch(`${BASE}/v1/harness/${ruleId}/approve`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ approved }),
  });
  if (!res.ok) throw new Error(`Approve failed: ${res.status}`);
  return res.json() as Promise<{ rule_id: string; status: string }>;
}

export async function submitScan(
  agentName: string,
  logs: Record<string, unknown>[],
  config: Record<string, unknown>,
): Promise<ScanResponse> {
  const res = await fetch(`${BASE}/v1/scan`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ agent_name: agentName, logs, config }),
  });
  if (!res.ok) throw new Error(`Scan failed: ${res.status}`);
  return res.json() as Promise<ScanResponse>;
}

// SWR fetcher helper — generic, so SWR can infer the Data type
export async function swrFetcher<T>(url: string): Promise<T> {
  const res = await fetch(`${BASE}${url}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json() as Promise<T>;
}
