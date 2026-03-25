import { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { fetchScores } from '../api';
import type { AsinScore, HealthLabel, Lifecycle } from '../types';
import { HEALTH_COLORS, HEALTH_LABELS_CN, LIFECYCLE_CN, healthLabelEmoji } from '../utils';

export default function Dashboard() {
  const [scores, setScores] = useState<AsinScore[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterLabel, setFilterLabel] = useState<string>('');
  const [filterLifecycle, setFilterLifecycle] = useState<string>('');
  const [sortField, setSortField] = useState<'trend_adjusted_score' | 'asin'>('trend_adjusted_score');
  const [sortAsc, setSortAsc] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchScores({ limit: 100 })
      .then(data => setScores(data.scores))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const stats = useMemo(() => {
    const counts: Record<HealthLabel, number> = { healthy: 0, warning: 0, abnormal: 0, danger: 0 };
    scores.forEach(s => { counts[s.health_label]++; });
    return counts;
  }, [scores]);

  const pieData = useMemo(() =>
    (['healthy', 'warning', 'abnormal', 'danger'] as HealthLabel[]).map(label => ({
      name: HEALTH_LABELS_CN[label],
      value: stats[label],
      color: HEALTH_COLORS[label],
    })),
  [stats]);

  const lifecycleData = useMemo(() => {
    const counts: Record<string, number> = {};
    scores.forEach(s => { counts[s.lifecycle] = (counts[s.lifecycle] || 0) + 1; });
    return (['new', 'growth', 'mature', 'decline'] as Lifecycle[]).map(lc => ({
      name: LIFECYCLE_CN[lc],
      count: counts[lc] || 0,
    }));
  }, [scores]);

  const filtered = useMemo(() => {
    let list = scores;
    if (filterLabel) list = list.filter(s => s.health_label === filterLabel);
    if (filterLifecycle) list = list.filter(s => s.lifecycle === filterLifecycle);
    list = [...list].sort((a, b) => {
      const va = sortField === 'asin' ? a.asin : a[sortField];
      const vb = sortField === 'asin' ? b.asin : b[sortField];
      if (va < vb) return sortAsc ? -1 : 1;
      if (va > vb) return sortAsc ? 1 : -1;
      return 0;
    });
    return list;
  }, [scores, filterLabel, filterLifecycle, sortField, sortAsc]);

  const toggleSort = (field: typeof sortField) => {
    if (sortField === field) setSortAsc(!sortAsc);
    else { setSortField(field); setSortAsc(field === 'asin'); }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-96 text-gray-400">加载中...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard label="总 ASIN" value={scores.length} color="#60a5fa" />
        <StatCard label="健康" value={stats.healthy} color={HEALTH_COLORS.healthy} />
        <StatCard label="预警" value={stats.warning} color={HEALTH_COLORS.warning} />
        <StatCard label="异常" value={stats.abnormal} color={HEALTH_COLORS.abnormal} />
        <StatCard label="危险" value={stats.danger} color={HEALTH_COLORS.danger} />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-[#1a1b23] rounded-lg p-4 border border-gray-800">
          <h3 className="text-gray-300 text-sm font-medium mb-3">健康分布</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={100}
                dataKey="value" nameKey="name" label={({ name, value }) => `${name}: ${value}`}>
                {pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Pie>
              <Tooltip contentStyle={{ background: '#1f2937', border: 'none', borderRadius: 8, color: '#e5e7eb' }} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-[#1a1b23] rounded-lg p-4 border border-gray-800">
          <h3 className="text-gray-300 text-sm font-medium mb-3">生命周期分布</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={lifecycleData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} />
              <Tooltip contentStyle={{ background: '#1f2937', border: 'none', borderRadius: 8, color: '#e5e7eb' }} />
              <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} name="数量" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Table */}
      <div className="bg-[#1a1b23] rounded-lg border border-gray-800">
        <div className="p-4 border-b border-gray-800 flex flex-wrap gap-3 items-center">
          <h3 className="text-gray-300 text-sm font-medium mr-auto">ASIN 评分排行</h3>
          <select value={filterLabel} onChange={e => setFilterLabel(e.target.value)}
            className="bg-[#0f1117] border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-300">
            <option value="">全部标签</option>
            {(['healthy', 'warning', 'abnormal', 'danger'] as HealthLabel[]).map(l => (
              <option key={l} value={l}>{HEALTH_LABELS_CN[l]}</option>
            ))}
          </select>
          <select value={filterLifecycle} onChange={e => setFilterLifecycle(e.target.value)}
            className="bg-[#0f1117] border border-gray-700 rounded px-3 py-1.5 text-sm text-gray-300">
            <option value="">全部周期</option>
            {(['new', 'growth', 'mature', 'decline'] as Lifecycle[]).map(l => (
              <option key={l} value={l}>{LIFECYCLE_CN[l]}</option>
            ))}
          </select>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800">
                <th className="px-4 py-3 text-left cursor-pointer hover:text-gray-200"
                  onClick={() => toggleSort('asin')}>
                  ASIN {sortField === 'asin' ? (sortAsc ? '\u25B2' : '\u25BC') : ''}
                </th>
                <th className="px-4 py-3 text-left">类目</th>
                <th className="px-4 py-3 text-left">生命周期</th>
                <th className="px-4 py-3 text-right cursor-pointer hover:text-gray-200"
                  onClick={() => toggleSort('trend_adjusted_score')}>
                  综合分 {sortField === 'trend_adjusted_score' ? (sortAsc ? '\u25B2' : '\u25BC') : ''}
                </th>
                <th className="px-4 py-3 text-center">健康标签</th>
                <th className="px-4 py-3 text-left">否决</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(s => (
                <tr key={s.asin}
                  className="border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer transition-colors"
                  onClick={() => navigate(`/asin/${s.asin}`)}>
                  <td className="px-4 py-3 font-mono text-blue-400">{s.asin}</td>
                  <td className="px-4 py-3 text-gray-400 max-w-48 truncate">{s.sub_category}</td>
                  <td className="px-4 py-3 text-gray-300">{LIFECYCLE_CN[s.lifecycle as Lifecycle]}</td>
                  <td className="px-4 py-3 text-right font-mono font-semibold"
                    style={{ color: HEALTH_COLORS[s.health_label] }}>
                    {s.trend_adjusted_score.toFixed(1)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium"
                      style={{ background: HEALTH_COLORS[s.health_label] + '20', color: HEALTH_COLORS[s.health_label] }}>
                      {healthLabelEmoji(s.health_label)} {HEALTH_LABELS_CN[s.health_label]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{s.veto_applied || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="bg-[#1a1b23] rounded-lg p-4 border border-gray-800">
      <div className="text-gray-400 text-xs mb-1">{label}</div>
      <div className="text-2xl font-bold" style={{ color }}>{value}</div>
    </div>
  );
}
