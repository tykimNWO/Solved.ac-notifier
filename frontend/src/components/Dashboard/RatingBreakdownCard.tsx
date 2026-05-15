import { useState } from 'react';
import { ChevronDown, ChevronUp, ListChecks } from 'lucide-react';
import type { LocalRatingResult, RatingProblem } from '../../types/dashboard';

interface RatingBreakdownCardProps {
  localRating?: LocalRatingResult;
}

const formatNumber = (value?: number | null) =>
  typeof value === 'number' ? value.toLocaleString() : '-';

const getTopProblemSummary = (problems: RatingProblem[]) => {
  if (problems.length === 0) {
    return { count: 0, minLevel: '-', maxLevel: '-', averageLevel: '-' };
  }
  const levels = problems.map((problem) => problem.level);
  const average = levels.reduce((sum, level) => sum + level, 0) / levels.length;
  return {
    count: problems.length,
    minLevel: Math.min(...levels).toString(),
    maxLevel: Math.max(...levels).toString(),
    averageLevel: average.toFixed(1),
  };
};

export function RatingBreakdownCard({ localRating }: RatingBreakdownCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const breakdown = localRating?.acRating;
  const topProblems = breakdown?.topProblems || [];
  const summary = getTopProblemSummary(topProblems);

  if (!breakdown) {
    return (
      <div className="rounded-2xl border border-gray-800 bg-[#1E1F20] p-5 text-sm text-gray-500">
        Local Rating 계산 데이터가 없습니다.
      </div>
    );
  }

  const rows = [
    { label: '상위 100문제 난이도 합', value: breakdown.topProblemScore },
    { label: 'CLASS 보너스', value: breakdown.classBonus },
    { label: '해결 문제 수 보너스', value: breakdown.solvedCountBonus },
    { label: '기여 보너스', value: breakdown.contributionBonus },
  ];

  return (
    <div className="rounded-2xl border border-gray-800 bg-[#1E1F20] p-5">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-gray-200">
            <ListChecks className="h-4 w-4 text-purple-300" />
            Rating Breakdown
          </div>
          <p className="mt-1 text-xs text-gray-500">
            {breakdown.classStatus || 'CLASS 상태 없음'} · rating 대상 {formatNumber(breakdown.solvedCountForRating)}문제
          </p>
        </div>
        <div className="text-right">
          <div className="text-xs text-gray-500">총합</div>
          <div className="text-2xl font-bold text-white">{formatNumber(breakdown.total)}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {rows.map((row) => (
          <div key={row.label} className="rounded-xl border border-white/5 bg-black/20 p-4">
            <div className="text-[11px] text-gray-500">{row.label}</div>
            <div className="mt-2 text-xl font-bold text-gray-100">{formatNumber(row.value)}</div>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-xl border border-white/5 bg-black/20 p-4">
        <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
          <div>
            <div className="text-gray-500">Top 100 반영</div>
            <div className="mt-1 font-bold text-gray-100">{summary.count}문제</div>
          </div>
          <div>
            <div className="text-gray-500">최저 level</div>
            <div className="mt-1 font-bold text-gray-100">{summary.minLevel}</div>
          </div>
          <div>
            <div className="text-gray-500">최고 level</div>
            <div className="mt-1 font-bold text-gray-100">{summary.maxLevel}</div>
          </div>
          <div>
            <div className="text-gray-500">평균 level</div>
            <div className="mt-1 font-bold text-gray-100">{summary.averageLevel}</div>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          className="mt-4 inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs text-gray-300 hover:bg-white/5"
        >
          {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          Top 문제 목록 {isOpen ? '접기' : '보기'}
        </button>
        {isOpen && (
          <div className="mt-4 max-h-72 overflow-y-auto custom-scrollbar">
            {topProblems.map((problem) => (
              <div key={`${problem.problemId}-${problem.solvedAt}`} className="grid grid-cols-[80px_1fr_68px] border-b border-white/5 py-2 text-xs">
                <div className="font-semibold text-blue-300">{problem.problemId}</div>
                <div className="truncate text-gray-300">{problem.title || '제목 없음'}</div>
                <div className="text-right font-bold text-gray-100">Lv. {problem.level}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
