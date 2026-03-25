import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { fetchScore } from '../api';
import type { AsinScore, Lifecycle } from '../types';
import { HEALTH_COLORS, HEALTH_LABELS_CN, LIFECYCLE_CN, DIMENSION_CN, healthLabelEmoji } from '../utils';

export default function AsinDetail() {
  const { asinId } = useParams<{ asinId: string }>();
  const navigate = useNavigate();
  const [score, setScore] = useState<AsinScore | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!asinId) return;
    fetchScore(asinId)
      .then(setScore)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [asinId]);

  if (loading) return <div className="flex items-center justify-center h-96 text-gray-400">加载中...</div>;
  if (error || !score) return <div className="text-red-400 text-center mt-20">{error || '未找到数据'}</div>;

  const radarData = Object.entries(DIMENSION_CN).map(([key, name]) => ({
    dimension: name,
    score: score.dimension_scores[key] ?? 0,
    fullMark: 100,
  }));

  const barData = Object.entries(DIMENSION_CN).map(([key, name]) => ({
    name,
    score: score.dimension_scores[key] ?? 0,
  }));

  const getBarColor = (val: number) => {
    if (val >= 80) return '#22c55e';
    if (val >= 60) return '#eab308';
    if (val >= 40) return '#f97316';
    return '#ef4444';
  };

  return (
    <div className="space-y-6">
      <button onClick={() => navigate('/')}
        className="text-gray-400 hover:text-gray-200 text-sm flex items-center gap-1 transition-colors">
        &larr; 返回列表
      </button>

      {/* Info Card */}
      <div className="bg-[#1a1b23] rounded-lg p-6 border border-gray-800">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-gray-100 font-mono">{score.asin}</h2>
            <p className="text-gray-400 text-sm mt-1">{score.sub_category}</p>
            <div className="flex flex-wrap gap-3 mt-3 text-sm">
              <span className="px-2 py-1 rounded bg-gray-800 text-gray-300">
                {LIFECYCLE_CN[score.lifecycle as Lifecycle]}
              </span>
              <span className="px-2 py-1 rounded bg-gray-800 text-gray-300">
                {score.date}
              </span>
            </div>
          </div>
          <div className="text-right">
            <div className="text-4xl font-bold font-mono" style={{ color: HEALTH_COLORS[score.health_label] }}>
              {score.trend_adjusted_score.toFixed(1)}
            </div>
            <span className="inline-flex items-center gap-1 mt-1 px-3 py-1 rounded-full text-sm font-medium"
              style={{ background: HEALTH_COLORS[score.health_label] + '20', color: HEALTH_COLORS[score.health_label] }}>
              {healthLabelEmoji(score.health_label)} {HEALTH_LABELS_CN[score.health_label]}
            </span>
          </div>
        </div>

        {score.veto_applied && (
          <div className="mt-4 p-3 rounded bg-red-900/20 border border-red-800/50 text-red-400 text-sm">
            <strong>否决规则触发：</strong>{score.veto_applied}
          </div>
        )}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-[#1a1b23] rounded-lg p-4 border border-gray-800">
          <h3 className="text-gray-300 text-sm font-medium mb-3">六维度雷达图</h3>
          <ResponsiveContainer width="100%" height={320}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#374151" />
              <PolarAngleAxis dataKey="dimension" tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#6b7280', fontSize: 10 }} />
              <Radar name="评分" dataKey="score" stroke="#6366f1" fill="#6366f1" fillOpacity={0.3} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-[#1a1b23] rounded-lg p-4 border border-gray-800">
          <h3 className="text-gray-300 text-sm font-medium mb-3">各维度分数</h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={barData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis type="number" domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <YAxis type="category" dataKey="name" width={80} tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <Tooltip contentStyle={{ background: '#1f2937', border: 'none', borderRadius: 8, color: '#e5e7eb' }}
                formatter={(value) => [Number(value).toFixed(1), '分数']} />
              <Bar dataKey="score" radius={[0, 4, 4, 0]}>
                {barData.map((entry, i) => <Cell key={i} fill={getBarColor(entry.score)} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Score Details Table */}
      <div className="bg-[#1a1b23] rounded-lg border border-gray-800 overflow-hidden">
        <h3 className="text-gray-300 text-sm font-medium p-4 border-b border-gray-800">评分明细</h3>
        <table className="w-full text-sm">
          <tbody>
            {Object.entries(DIMENSION_CN).map(([key, name]) => {
              const val = score.dimension_scores[key] ?? 0;
              return (
                <tr key={key} className="border-b border-gray-800/50">
                  <td className="px-4 py-3 text-gray-400">{name}</td>
                  <td className="px-4 py-3 text-right font-mono font-semibold" style={{ color: getBarColor(val) }}>
                    {val.toFixed(1)}
                  </td>
                  <td className="px-4 py-3 w-1/2">
                    <div className="bg-gray-800 rounded-full h-2 overflow-hidden">
                      <div className="h-full rounded-full transition-all" style={{ width: `${val}%`, background: getBarColor(val) }} />
                    </div>
                  </td>
                </tr>
              );
            })}
            <tr className="bg-gray-800/20">
              <td className="px-4 py-3 text-gray-300 font-medium">加权综合分</td>
              <td className="px-4 py-3 text-right font-mono font-bold" style={{ color: HEALTH_COLORS[score.health_label] }}>
                {score.weighted_score.toFixed(1)}
              </td>
              <td />
            </tr>
            <tr className="bg-gray-800/20">
              <td className="px-4 py-3 text-gray-300 font-medium">最终评分（含否决）</td>
              <td className="px-4 py-3 text-right font-mono font-bold" style={{ color: HEALTH_COLORS[score.health_label] }}>
                {score.final_score.toFixed(1)}
              </td>
              <td />
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
