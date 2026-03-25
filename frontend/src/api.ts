import type { AsinScore, DiagnosisResponse, ProblemDimension, ScoreListResponse } from './types';

const BASE_URL = import.meta.env.VITE_API_URL ?? '';

export async function fetchScores(params?: {
  health_label?: string;
  lifecycle?: string;
  limit?: number;
}): Promise<ScoreListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.health_label) searchParams.set('health_label', params.health_label);
  if (params?.lifecycle) searchParams.set('lifecycle', params.lifecycle);
  if (params?.limit) searchParams.set('limit', String(params.limit));
  const qs = searchParams.toString();
  const res = await fetch(`${BASE_URL}/scores${qs ? '?' + qs : ''}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchScore(asinId: string): Promise<AsinScore> {
  const res = await fetch(`${BASE_URL}/scores/${asinId}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchDiagnosis(asinId: string, force: boolean = false): Promise<DiagnosisResponse> {
  // Step 1: Start diagnosis (returns immediately with problem_overview + task_id, or cached result)
  const qs = force ? '?force=true' : '';
  const startRes = await fetch(`${BASE_URL}/diagnosis/${asinId}${qs}`, { method: 'POST' });
  if (!startRes.ok) throw new Error(`API error: ${startRes.status}`);
  const startData = await startRes.json();

  // 缓存命中：直接返回
  if (startData.from_cache && startData.status === 'done') {
    return startData.result as DiagnosisResponse;
  }

  const taskId = startData.task_id;

  // Step 2: Poll for result every 3 seconds (max 120s)
  const maxAttempts = 40;
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise(r => setTimeout(r, 3000));
    const pollRes = await fetch(`${BASE_URL}/diagnosis/result/${taskId}`);
    if (!pollRes.ok) throw new Error(`Poll error: ${pollRes.status}`);
    const pollData = await pollRes.json();

    if (pollData.status === 'done') {
      return pollData.result as DiagnosisResponse;
    }
    if (pollData.status === 'error') {
      throw new Error(pollData.result || 'Diagnosis failed');
    }
    // status === 'running', continue polling
  }
  throw new Error('Diagnosis timeout');
}

// Start diagnosis and get immediate problem overview
export async function startDiagnosis(asinId: string, force: boolean = false): Promise<{ task_id: string; from_cache?: boolean; result?: DiagnosisResponse; problem_overview?: { asin: string; health_label: string; final_score: number; summary: string; problem_dimensions: ProblemDimension[] } }> {
  const qs = force ? '?force=true' : '';
  const res = await fetch(`${BASE_URL}/diagnosis/${asinId}${qs}`, { method: 'POST' });
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
