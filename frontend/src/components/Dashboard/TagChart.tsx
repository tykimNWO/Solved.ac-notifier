import { Tag } from 'lucide-react';
import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from 'recharts';
import type { DashboardStats } from '../../types/dashboard';

interface TagChartProps {
  data: DashboardStats['tagDistribution'];
  totalSolved: number;
}

const formatPercent = (value?: number) =>
  typeof value === 'number' ? `${value.toFixed(1)}%` : '0.0%';

const formatRating = (value?: number) =>
  typeof value === 'number' ? value.toLocaleString() : '0';

const getDisplayTag = (tagName: string) => `#${tagName}`;

export function TagChart({ data, totalSolved }: TagChartProps) {
  const hasData = data.some((item) => item.count > 0);
  const chartData = data.map((item) => ({
    ...item,
    displayTag: item.tag.replace(/_/g, '_'),
    rating: item.rating || 0,
  }));

  return (
    <div className="rounded-2xl border border-gray-800 bg-[#091216] p-5 lg:col-span-2">
      <div className="mb-5 flex items-center gap-2 text-sm font-semibold text-gray-300">
        <Tag className="h-4 w-4" />
        태그 분포
      </div>

      {hasData ? (
        <div className="grid grid-cols-1 gap-8 xl:grid-cols-[minmax(320px,0.9fr)_minmax(520px,1.1fr)]">
          <div className="h-[420px] min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={chartData} outerRadius="74%">
                <PolarGrid gridType="polygon" stroke="#334155" strokeDasharray="6 6" />
                <PolarAngleAxis dataKey="displayTag" tick={{ fill: '#e5e7eb', fontSize: 12 }} />
                <PolarRadiusAxis angle={90} domain={[0, 800]} tick={{ fill: '#9ca3af', fontSize: 11 }} stroke="#334155" />
                <Radar
                  name="레이팅"
                  dataKey="rating"
                  stroke="#f0a500"
                  fill="#f0a500"
                  fillOpacity={0.12}
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: '#f0a500', strokeWidth: 0 }}
                />
                <Tooltip
                  formatter={(value, name) => [formatRating(Number(value)), name]}
                  labelFormatter={(label) => `태그: ${label}`}
                  contentStyle={{ background: '#131314', border: '1px solid #374151', borderRadius: 12, color: '#f3f4f6' }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          <div className="min-w-0 overflow-hidden">
            <div className="grid grid-cols-[minmax(160px,1fr)_86px_106px] border-b border-white/10 px-3 pb-3 text-xs font-semibold text-gray-300">
              <div>태그</div>
              <div className="text-right">문제</div>
              <div className="text-right">레이팅</div>
            </div>
            <div className="max-h-[420px] overflow-y-auto custom-scrollbar">
              {data.map((item) => (
                <div key={item.tag} className="grid grid-cols-[minmax(160px,1fr)_86px_106px] border-b border-white/10 px-3 py-3 text-sm">
                  <div className="truncate pr-3 text-gray-100">{getDisplayTag(item.tag)}</div>
                  <div className="text-right">
                    <span className="font-semibold text-gray-100">{item.count.toLocaleString()}</span>
                    <span className="ml-3 text-gray-400">{formatPercent(item.percent)}</span>
                  </div>
                  <div className="flex items-center justify-end gap-2 font-bold text-[#55799b]">
                    <span className="inline-flex h-5 min-w-5 items-center justify-center rounded bg-[#55799b]/80 px-1 text-[11px] text-white">
                      {item.rank || 5}
                    </span>
                    {formatRating(item.rating)}
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-4 text-xs leading-relaxed text-gray-500">
              레이팅은 로컬 solved 로그의 풀이 수와 난이도 가중치를 800점 스케일로 정규화한 대시보드용 지표입니다.
              총 {totalSolved.toLocaleString()}문제 기준으로 계산했습니다.
            </p>
          </div>
        </div>
      ) : (
        <div className="flex h-72 items-center justify-center rounded-xl border border-dashed border-gray-800 text-sm text-gray-500">
          태그 데이터가 없습니다
        </div>
      )}
    </div>
  );
}
