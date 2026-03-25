import { useState } from 'react';
import { fetchDiagnosis } from '../api';
import type { DiagnosisResponse, ActionItem } from '../types';

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

function SkeletonCard() {
  return (
    <div className="bg-[#1a1b23] rounded-lg p-6 border border-gray-800 animate-pulse">
      <div className="h-4 bg-gray-700 rounded w-1/3 mb-4" />
      <div className="space-y-3">
        <div className="h-3 bg-gray-700/60 rounded w-full" />
        <div className="h-3 bg-gray-700/60 rounded w-5/6" />
        <div className="h-3 bg-gray-700/60 rounded w-2/3" />
      </div>
    </div>
  );
}

export default function DiagnosisPanel({ asinId }: { asinId: string }) {
  const [data, setData] = useState<DiagnosisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleRun = () => {
    setLoading(true);
    setError('');
    setData(null);
    fetchDiagnosis(asinId)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  };

  return (
    <div className="space-y-4">
      {/* Trigger */}
      <div className="flex items-center justify-between">
        <h3 className="text-gray-200 font-semibold text-lg">
          {'\uD83D\uDD0D'} 智能诊断
        </h3>
        <button
          onClick={handleRun}
          disabled={loading}
          className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
        >
          {loading ? 'AI 正在分析中...' : data ? '重新诊断' : '开始诊断'}
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="space-y-4">
          <div className="text-center text-gray-400 text-sm py-2">
            {'\u2728'} AI Agent 正在分析中，请稍候...
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-4 text-red-400 text-sm">
          诊断失败: {error}
        </div>
      )}

      {/* Results */}
      {data && !loading && (
        <div className="space-y-4">

          {/* Card 1: 问题概览 */}
          <div className="bg-[#1a1b23] rounded-lg p-6 border border-gray-800">
            <h4 className="text-gray-400 text-xs font-medium uppercase tracking-wider mb-3">
              {'\u26A0\uFE0F'} 问题概览
            </h4>
            <p className="text-gray-100 text-lg font-medium mb-4">{data.summary}</p>
            {data.problem_dimensions.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {data.problem_dimensions.map(p => {
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

          {/* Card 2: 根因分析 */}
          <div className="bg-[#1a1b23] rounded-lg p-6 border border-gray-800">
            <h4 className="text-gray-400 text-xs font-medium uppercase tracking-wider mb-4">
              {'\uD83E\uDDE0'} 根因分析
            </h4>
            <div className="space-y-3">
              {data.root_causes.map((rc, i) => {
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

          {/* Card 3: 行动建议 */}
          <div className="bg-[#1a1b23] rounded-lg p-6 border border-gray-800">
            <h4 className="text-gray-400 text-xs font-medium uppercase tracking-wider mb-4">
              {'\uD83D\uDCCB'} 行动建议
            </h4>
            <div className="space-y-3">
              {data.action_plan.map((item, i) => (
                <ActionCard key={i} item={item} />
              ))}
            </div>
          </div>

          {/* Card 4: 竞品对标 */}
          <div className="bg-[#1a1b23] rounded-lg p-6 border border-gray-800">
            <h4 className="text-gray-400 text-xs font-medium uppercase tracking-wider mb-3">
              {'\uD83C\uDFC6'} 竞品对标
            </h4>
            <div className="mb-3">
              <span className="text-gray-400 text-sm">类目位置: </span>
              <span className="text-gray-200 font-medium">{data.benchmark.category_position}</span>
            </div>
            {data.benchmark.weak_vs_benchmark.length > 0 && (
              <div className="mb-3">
                <div className="text-gray-400 text-sm mb-1.5">弱于基准的维度:</div>
                <ul className="space-y-1">
                  {data.benchmark.weak_vs_benchmark.map((w, i) => (
                    <li key={i} className="text-orange-400 text-sm flex items-start gap-2">
                      <span className="mt-0.5">{'\u25BC'}</span>
                      <span>{w}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="bg-gray-800/30 rounded-lg p-3 text-gray-300 text-sm whitespace-pre-wrap">
              {data.benchmark.competitor_insights}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
