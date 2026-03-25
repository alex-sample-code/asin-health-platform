import type { AsinScore, DiagnosisResponse, ScoreListResponse } from './types';

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export async function fetchScores(params?: {
  health_label?: string;
  lifecycle?: string;
  limit?: number;
}): Promise<ScoreListResponse> {
  const url = new URL(`${BASE_URL}/scores`);
  if (params?.health_label) url.searchParams.set('health_label', params.health_label);
  if (params?.lifecycle) url.searchParams.set('lifecycle', params.lifecycle);
  if (params?.limit) url.searchParams.set('limit', String(params.limit));
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchScore(asinId: string): Promise<AsinScore> {
  const res = await fetch(`${BASE_URL}/scores/${asinId}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchDiagnosis(asinId: string): Promise<DiagnosisResponse> {
  const res = await fetch(`${BASE_URL}/diagnosis/${asinId}`, { method: 'POST' });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function sendChat(message: string): Promise<string> {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  const data = await res.json();
  return data.response;
}
