import type { AsinScore, DiagnosisResponse, ScoreListResponse } from './types';

const BASE_URL = import.meta.env.VITE_API_URL ?? '';

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

export interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
}

export async function streamDiagnosis(
  asinId: string,
  onEvent: (evt: SSEEvent) => void,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/diagnosis/${asinId}`, { method: 'POST' });
  if (!res.ok) throw new Error(`API error: ${res.status}`);

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // 解析 SSE：每个事件以 \n\n 分隔
    const parts = buffer.split('\n\n');
    // 最后一个可能不完整，留在 buffer
    buffer = parts.pop() ?? '';

    for (const part of parts) {
      if (!part.trim()) continue;
      let eventName = 'message';
      let dataStr = '';
      for (const line of part.split('\n')) {
        if (line.startsWith('event: ')) {
          eventName = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          dataStr = line.slice(6);
        }
      }
      if (dataStr) {
        try {
          onEvent({ event: eventName, data: JSON.parse(dataStr) });
        } catch {
          // JSON 解析失败，跳过
        }
      }
    }
  }
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
