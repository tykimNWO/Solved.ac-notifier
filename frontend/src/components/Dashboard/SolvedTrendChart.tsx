import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { DashboardStats } from '../../types/dashboard';

interface SolvedTrendChartProps {
  data?: DashboardStats['dailySolvedTrend'];
}

const formatTick = (value: string) => value.slice(5);

export function SolvedTrendChart({ data = [] }: SolvedTrendChartProps) {
  const hasData = data.some((item) => item.count > 0);

  return (
    <div className="rounded-2xl border border-gray-800 bg-[#1E1F20] p-5 lg:col-span-2">
      <div className="mb-4">
        <h3 className="text-sm font-bold text-white">최근 풀이 추세</h3>
        <p className="mt-1 text-xs text-gray-500">최근 30일 로컬 풀이 기록</p>
      </div>
      {hasData ? (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid stroke="#2f3136" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="date" tickFormatter={formatTick} stroke="#9ca3af" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} stroke="#9ca3af" tick={{ fontSize: 11 }} />
              <Tooltip
                labelFormatter={(value) => `날짜: ${value}`}
                cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                contentStyle={{ background: '#131314', border: '1px solid #374151', borderRadius: 12, color: '#f3f4f6' }}
              />
              <Bar dataKey="count" fill="#22c55e" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="flex h-64 items-center justify-center rounded-xl border border-dashed border-gray-800 text-sm text-gray-500">
          최근 30일 풀이 기록이 없습니다
        </div>
      )}
    </div>
  );
}
