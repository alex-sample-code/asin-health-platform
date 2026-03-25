import { useCallback, useRef, useState } from 'react';
import { startDiagnosis } from '../api';
import type { ActionItem, BenchmarkComparison, DiagnosisResponse, ProblemDimension, RootCause } from '../types';

const SEVERITY_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  critical: { bg: 'bg-red-900/30', text: 'text-red-400', label: '严重' },
  warning: { bg: 'bg-orange-900/30', text: 'text-orange-400', label: '警告' },
  attention: { bg: 'bg-yellow-900/30', text: 'text-yellow-400', label: '关注' },
};

const CONFIDENCE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  high: { bg: 'bg-green-900/30', text: 'text-green-400', label: '高' },
  medium: { bg: 'bg-yellow-900/30', text: 'text-yellow-400', label: '中' },
  low: { bg: 'bg-gray-800', text: 'text-gray-400', label: '低' },
};

const PRIORITY_BORDER: Record<string, string> = {
  P0: 'border-l-red-500',
  P1: 'border-l-orange-500',
  P2: 'border-l-yellow-500',
  P3: 'border-l-blue-500',
};

const PRIORITY_BADGE: Record<string, { bg: string; text: string }> = {
  P0: { bg: 'bg-red-900/30', text: 'text-red-400' },
  P1: { bg: 'bg-orange-900/30', text: 'text-orange-400' },
  P2: { bg: 'bg-yellow-900/30', text: 'text-yellow-400' },
  P3: { bg: 'bg-blue-900/30', text: 'text-blue-400' },
};

// ── 子组件 ────────────────────────────────────────────────────────────────

function Spinner() {
  return (
    <svg className="animate-spin h-4 w-4 text-indigo-400" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

function SkeletonCard({ title }: { title: string }) {
  return (
    <div className="bg-[#1a1b23] rounded-lg p-6 border border-gray-800 animate-pulse">
      <div className="flex items-center gap-2 mb-4">
        <Spinner />
        <span className="text-gray-500 text-xs font-medium uppercase tracking-wider">{title}</span>
      </div>
      <div className="space-y-3">
        <div className="h-3 bg-gray-700/60 rounded w-full" />
        <div className="h-3 bg-gray-700/60 rounded w-5/6" />
        <div className="h-3 bg-gray-700/60 rounded w-2/3" />
      </div>
    </div>
  );
}

function ErrorCard({ title, message }: { title: string; message: string }) {
  return (
    <div className="bg-[#1a1b23] rounded-lg p-6 border border-red-800/50">
      <h4 className="text-red-400 text-xs font-medium uppercase tracking-wider mb-3">{title}</h4>
      <p className="text-red-400/80 text-sm">{message}</p>
    </div>
  );
}

function ActionCard({ item }: { item: ActionItem }) {
  const [expanded, setExpanded] = useState(false);
  const border = PRIORITY_BORDER[item.priority] ?? 'border-l-gray-500';
  const badge = PRIORITY_BADGE[item.priority] ?? { bg: 'bg-gray-800', text: 'text-gray-400' };

  return (
    <div className={`bg-[#1a1b23] rounded-lg border border-gray-800 border-l-4 ${border} overflow-hidden`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4 flex items-start justify-between gap-3 hover:bg-gray-800/30 transition-colors"
      >
        <div className="flex items-start gap-3 min-w-0">
          <span className={`shrink-0 px-2 py-0.5 rounded text-xs font-semibold ${badge.bg} ${badge.text}`}>
            {item.priority}
          </span>
          <div className="min-w-0">
            <div className="text-gray-200 font-medium">{item.title}</div>
            <div className="text-gray-500 text-xs mt-1">{item.timeline}</div>
          </div>
        </div>
        <span className="text-gray-500 shrink-0 mt-1">{expanded ? '\u25B2' : '\u25BC'}</span>
      </button>
      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          {item.steps.length > 0 && (
            <div>
              <div className="text-gray-400 text-xs font-medium mb-1.5">具体步骤</div>
              <ol className="space-y-1 text-sm text-gray-300 list-decimal list-inside">
                {item.steps.map((s, i) => <li key={i}>{s}</li>)}
              </ol>
            </div>
          )}
          <div className="text-sm">
            <span className="text-gray-400">预期效果: </span>
            <span className="text-gray-300">{item.expected_effect}</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ── 各阶段状态类型 ────────────────────────────────────────────────────────

interface ProblemOverview {
  summary: string;
  problem_dimensions: ProblemDimension[];
  health_label: string;
  final_score: number;
}

interface ModuleError {
  module: string;
  message: string;
}

// ── 主组件 ────────────────────────────────────────────────────────────────

export default function DiagnosisPanel({ asinId }: { asinId: string }) {
  const [running, setRunning] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);

  const [problemOverview, setProblemOverview] = useState<ProblemOverview | null>(null);
  const [rootCauses, setRootCauses] = useState<RootCause[] | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkComparison | null>(null);
  const [actionPlan, setActionPlan] = useState<ActionItem[] | null>(null);

  const [errors, setErrors] = useState<ModuleError[]>([]);
  const [streamError, setStreamError] = useState('');

  const errorsRef = useRef<ModuleError[]>([]);

  const handleRun = useCallback(() => {
    setRunning(true);
    setHasStarted(true);
    setProblemOverview(null);
    setRootCauses(null);
    setBenchmark(null);
    setActionPlan(null);
    setErrors([]);
    setStreamError('');
    errorsRef.current = [];

    const BASE_URL = import.meta.env.VITE_API_URL ?? '';

    // Step 1: 立即获取问题概览
    startDiagnosis(asinId)
      .then(async (startData) => {
        // 立即显示问题概览
        setProblemOverview({
          summary: startData.problem_overview.summary,
          health_label: startData.problem_overview.health_label,
          final_score: startData.problem_overview.final_score,
          problem_dimensions: startData.problem_overview.problem_dimensions,
        });

        // Step 2: 轮询完整结果
        const taskId = startData.task_id;
        const maxAttempts = 40;
        for (let i = 0; i < maxAttempts; i++) {
          await new Promise(r => setTimeout(r, 3000));
          const pollRes = await fetch(`${BASE_URL}/diagnosis/result/${taskId}`);
          if (!pollRes.ok) {
            setStreamError(`Poll error: ${pollRes.status}`);
            setRunning(false);
            return;
          }
          const pollData = await pollRes.json();

          if (pollData.status === 'done') {
            const result = pollData.result as DiagnosisResponse;
            if (result.root_causes?.length) setRootCauses(result.root_causes);
            if (result.benchmark) setBenchmark(result.benchmark);
            if (result.action_plan?.length) setActionPlan(result.action_plan);
            setRunning(false);
            return;
          }
          if (pollData.status === 'error') {
            setStreamError(pollData.result || 'Diagnosis failed');
            setRunning(false);
            return;
          }
          // status === 'running', continue
        }
        setStreamError('诊断超时，请重试');
        setRunning(false);
      })
      .catch((e) => {
        setStreamError(e.message || 'network error');
        setRunning(false);
      });
  }, [asinId]);

  const hasError = (module: string) => errors.some((e) => e.module === module);
  const getError = (module: string) => errors.find((e) => e.module === module);

  return (
    <div className="space-y-4">
      {/* Trigger */}
      <div className="flex items-center justify-between">
        <h3 className="text-gray-200 font-semibold text-lg">
          {'\uD83D\uDD0D'} 智能诊断
        </h3>
        <button
          onClick={handleRun}
          disabled={running}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
        >
          {running ? 'AI 正在分析中...' : hasStarted ? '重新诊断' : '开始诊断'}
        </button>
      </div>

      {/* Stream-level error */}
      {streamError && (
        <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-4 text-red-400 text-sm">
          诊断失败: {streamError}
        </div>
      )}

      {/* 阶段性渲染 */}
      {hasStarted && !streamError && (
        <div className="space-y-4">

          {/* Card 1: 问题概览 */}
          {problemOverview ? (
            <div className="bg-[#1a1b23] rounded-lg p-6 border border-gray-800">
              <h4 className="text-gray-400 text-xs font-medium uppercase tracking-wider mb-3">
                {'\u26A0\uFE0F'} 问题概览
              </h4>
              <p className="text-gray-100 text-lg font-medium mb-4">{problemOverview.summary}</p>
              {problemOverview.problem_dimensions.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {problemOverview.problem_dimensions.map((p) => {
                    const style = SEVERITY_STYLES[p.severity] ?? SEVERITY_STYLES.attention;
                    return (
                      <div key={p.dimension}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg ${style.bg} border border-gray-700`}>
                        <span className={`text-sm font-semibold ${style.text}`}>{p.dimension_cn}</span>
                        <span className="text-gray-400 font-mono text-sm">{p.score}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${style.bg} ${style.text}`}>
                          {style.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ) : (
            running && <SkeletonCard title="问题概览" />
          )}

          {/* Card 2: 根因分析 */}
          {rootCauses ? (
            <div className="bg-[#1a1b23] rounded-lg p-6 border border-gray-800">
              <h4 className="text-gray-400 text-xs font-medium uppercase tracking-wider mb-4">
                {'\uD83E\uDDE0'} 根因分析
              </h4>
              <div className="space-y-3">
                {rootCauses.map((rc, i) => {
                  const conf = CONFIDENCE_STYLES[rc.confidence] ?? CONFIDENCE_STYLES.medium;
                  return (
                    <div key={i} className="bg-gray-800/30 rounded-lg p-4 border border-gray-700/50">
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <p className="text-gray-200 font-medium">{rc.hypothesis}</p>
                        <span className={`shrink-0 px-2 py-0.5 rounded text-xs font-medium ${conf.bg} ${conf.text}`}>
                          置信度: {conf.label}
                        </span>
                      </div>
                      {rc.evidence.length > 0 && (
                        <ul className="space-y-1 mt-2">
                          {rc.evidence.map((e, j) => (
                            <li key={j} className="text-gray-400 text-sm flex items-start gap-2">
                              <span className="text-gray-600 mt-0.5">{'\u2022'}</span>
                              <span>{e}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ) : hasError('root_cause') ? (
            <ErrorCard title="根因分析" message={getError('root_cause')!.message} />
          ) : (
            running && <SkeletonCard title="根因分析" />
          )}

          {/* Card 3: 竞品对标 */}
          {benchmark ? (
            <div className="bg-[#1a1b23] rounded-lg p-6 border border-gray-800">
              <h4 className="text-gray-400 text-xs font-medium uppercase tracking-wider mb-3">
                {'\uD83C\uDFC6'} 竞品对标
              </h4>
              <div className="mb-3">
                <span className="text-gray-400 text-sm">类目位置: </span>
                <span className="text-gray-200 font-medium">{benchmark.category_position}</span>
              </div>
              {benchmark.weak_vs_benchmark.length > 0 && (
                <div className="mb-3">
                  <div className="text-gray-400 text-sm mb-1.5">弱于基准的维度:</div>
                  <ul className="space-y-1">
                    {benchmark.weak_vs_benchmark.map((w, i) => (
                      <li key={i} className="text-orange-400 text-sm flex items-start gap-2">
                        <span className="mt-0.5">{'\u25BC'}</span>
                        <span>{w}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="bg-gray-800/30 rounded-lg p-3 text-gray-300 text-sm whitespace-pre-wrap">
                {benchmark.competitor_insights}
              </div>
            </div>
          ) : hasError('benchmark') ? (
            <ErrorCard title="竞品对标" message={getError('benchmark')!.message} />
          ) : (
            running && <SkeletonCard title="竞品对标" />
          )}

          {/* Card 4: 行动建议 */}
          {actionPlan ? (
            <div className="bg-[#1a1b23] rounded-lg p-6 border border-gray-800">
              <h4 className="text-gray-400 text-xs font-medium uppercase tracking-wider mb-4">
                {'\uD83D\uDCCB'} 行动建议
              </h4>
              <div className="space-y-3">
                {actionPlan.map((item, i) => (
                  <ActionCard key={i} item={item} />
                ))}
              </div>
            </div>
          ) : hasError('action_plan') ? (
            <ErrorCard title="行动建议" message={getError('action_plan')!.message} />
          ) : (
            running && <SkeletonCard title="行动建议" />
          )}
        </div>
      )}
    </div>
  );
}
