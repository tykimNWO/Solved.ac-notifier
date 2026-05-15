import { Tag } from 'lucide-react';
import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from 'recharts';
import type { TagRatingBreakdown } from '../../types/dashboard';

interface TagChartProps {
  data?: TagRatingBreakdown[];
  totalSolved: number;
}

const formatRating = (value?: number) =>
  typeof value === 'number' ? value.toLocaleString() : '0';

const getDisplayTag = (tagName: string) => `#${tagName}`;

export function TagChart({ data, totalSolved }: TagChartProps) {
  const tagRatings = data || [];
  const hasData = tagRatings.some((item) => item.rating > 0);
  const maxRating = Math.max(800, ...tagRatings.map((item) => item.rating));
  const chartData = tagRatings.map((item) => ({
    ...item,
    displayTag: item.tag.replace(/_/g, '_'),
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
                <PolarRadiusAxis angle={90} domain={[0, maxRating]} tick={{ fill: '#9ca3af', fontSize: 11 }} stroke="#334155" />
                <Radar
                  name="Local Tag Rating"
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

          <div className="min-w-0 overflow-x-auto custom-scrollbar">
            <div className="min-w-[620px]">
            <div className="grid grid-cols-[minmax(150px,1fr)_76px_104px_104px_104px] border-b border-white/10 px-3 pb-3 text-xs font-semibold text-gray-300">
              <div>태그</div>
              <div className="text-right">문제</div>
              <div className="text-right">Top 50</div>
              <div className="text-right">보너스</div>
              <div className="text-right">레이팅</div>
            </div>
            <div className="max-h-[420px] overflow-y-auto custom-scrollbar">
              {tagRatings.map((item) => (
                <div key={item.tag} className="grid grid-cols-[minmax(150px,1fr)_76px_104px_104px_104px] border-b border-white/10 px-3 py-3 text-sm">
                  <div className="truncate pr-3 text-gray-100">{getDisplayTag(item.tag)}</div>
                  <div className="text-right">
                    <span className="font-semibold text-gray-100">{item.solvedCount.toLocaleString()}</span>
                  </div>
                  <div className="text-right font-semibold text-gray-300">{formatRating(item.topProblemScore)}</div>
                  <div className="text-right font-semibold text-gray-300">{formatRating(item.solvedCountBonus)}</div>
                  <div className="flex items-center justify-end gap-2 font-bold text-[#55799b]">
                    <span className="inline-flex h-5 min-w-5 items-center justify-center rounded bg-[#55799b]/80 px-1 text-[11px] text-white">
                      L
                    </span>
                    {formatRating(item.rating)}
                  </div>
                </div>
              ))}
            </div>
            </div>
            <p className="mt-4 text-xs leading-relaxed text-gray-500">
              레이팅은 태그 내 상위 50문제 level 합 * 2와 해결 수 보너스를 더한 Local Tag Rating입니다.
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
