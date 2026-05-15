import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import type { DashboardStats } from '../../types/dashboard';

interface DifficultyChartProps {
  data: DashboardStats['difficultyDistribution'];
  totalSolved: number;
}

const tierColors: Record<string, string> = {
  NR: '#6b7280',
  B: '#ad5600',
  S: '#435f7a',
  G: '#ec9a00',
  P: '#27e2a4',
  D: '#00b4fc',
  R: '#ff0062',
};

const tierTextColors: Record<string, string> = {
  NR: 'text-gray-300',
  B: 'text-[#c46b13]',
  S: 'text-[#55799b]',
  G: 'text-[#f0a500]',
  P: 'text-[#27e2a4]',
  D: 'text-[#00b4fc]',
  R: 'text-[#ff4a91]',
};

const getTierFamily = (tier: string) => tier === 'NR' ? 'NR' : tier.slice(0, 1);

const formatPercent = (count: number, total: number) =>
  total > 0 ? `${((count / total) * 100).toFixed(1)}%` : '0.0%';

const getSliceColor = (tier: string, index: number) => {
  const family = getTierFamily(tier);
  const base = tierColors[family] || tierColors.NR;
  const opacity = 0.55 + ((index % 5) * 0.09);
  return `${base}${Math.round(opacity * 255).toString(16).padStart(2, '0')}`;
};

const RADIAN = Math.PI / 180;

interface PieLabelProps {
  cx?: number;
  cy?: number;
  midAngle?: number;
  outerRadius?: number;
  percent?: number;
  payload?: {
    tier?: string;
  };
}

const renderTierLabel = (props: PieLabelProps) => {
  const { cx = 0, cy = 0, midAngle = 0, outerRadius = 0, percent = 0, payload } = props;
  if (!payload?.tier || percent < 0.015) return null;
  const radius = outerRadius * 0.72;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="#f8fafc"
      textAnchor="middle"
      dominantBaseline="central"
      className="text-[11px] font-bold"
    >
      {payload.tier}
    </text>
  );
};

export function DifficultyChart({ data, totalSolved }: DifficultyChartProps) {
  const hasData = data.some((item) => item.count > 0);
  const chartData = data.filter((item) => item.count > 0);

  return (
    <div className="rounded-2xl border border-gray-800 bg-[#091216] p-5 lg:col-span-2">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-gray-300">
            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-gray-500 text-[10px]">△</span>
            난이도 분포
          </div>
          <div className="mt-3 text-3xl font-bold text-white">
            {totalSolved.toLocaleString()}<span className="ml-1 text-xl font-semibold text-gray-200">문제 해결</span>
          </div>
        </div>
      </div>

      {hasData ? (
        <div className="grid grid-cols-1 gap-8 xl:grid-cols-[minmax(320px,0.9fr)_minmax(420px,1.1fr)]">
          <div className="relative h-[360px] min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  dataKey="count"
                  nameKey="tier"
                  cx="50%"
                  cy="50%"
                  innerRadius="36%"
                  outerRadius="74%"
                  paddingAngle={0}
                  stroke="#091216"
                  strokeWidth={1}
                  label={renderTierLabel}
                  labelLine={false}
                >
                  {chartData.map((entry, index) => (
                    <Cell key={entry.tier} fill={getSliceColor(entry.tier, index)} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value, _name, item) => [`${value}문제`, item.payload.tier]}
                  contentStyle={{ background: '#131314', border: '1px solid #374151', borderRadius: 12, color: '#f3f4f6' }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full border border-blue-400/30 bg-[#111827] text-sm font-bold text-blue-200 shadow-lg shadow-blue-500/10">
                {totalSolved}
              </div>
            </div>
          </div>

          <div className="min-w-0 overflow-hidden">
            <div className="grid grid-cols-[1fr_80px_76px] border-b border-white/10 px-3 pb-3 text-xs font-semibold text-gray-300">
              <div>레벨</div>
              <div className="text-right">문제</div>
              <div className="text-right">비율</div>
            </div>
            <div className="max-h-[360px] overflow-y-auto custom-scrollbar">
              {data.map((item) => {
                const family = getTierFamily(item.tier);
                return (
                  <div key={item.tier} className="grid grid-cols-[1fr_80px_76px] border-b border-white/10 px-3 py-3 text-sm">
                    <div className={`font-bold ${tierTextColors[family] || tierTextColors.NR}`}>{item.tier}</div>
                    <div className="text-right font-bold text-gray-100">{item.count.toLocaleString()}</div>
                    <div className="text-right text-gray-400">{formatPercent(item.count, totalSolved)}</div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex h-72 items-center justify-center rounded-xl border border-dashed border-gray-800 text-sm text-gray-500">
          난이도 데이터가 없습니다
        </div>
      )}
    </div>
  );
}
