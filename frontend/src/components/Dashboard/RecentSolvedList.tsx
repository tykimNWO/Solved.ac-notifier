import { useState } from 'react';
import { FileCode2 } from 'lucide-react';
import type { LocalSolvedProblem } from '../../types/dashboard';

interface RecentSolvedListProps {
  problems: LocalSolvedProblem[];
  onOpenProblem: (problemId: number | string) => void;
}

export function RecentSolvedList({ problems, onOpenProblem }: RecentSolvedListProps) {
  const [isDetailed, setIsDetailed] = useState(false);
  const visibleProblems = isDetailed ? problems : problems.slice(0, 5);

  return (
    <div className="rounded-2xl border border-gray-800 bg-[#1E1F20] p-5">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-sm font-bold text-white">최근 푼 문제</h3>
          <p className="mt-1 text-xs text-gray-500">
            {isDetailed ? '로컬 solved 로그 최신순 상세 목록' : '최근 풀이를 빠르게 훑어보는 간략 목록'}
          </p>
        </div>
        {problems.length > 5 && (
          <button
            type="button"
            onClick={() => setIsDetailed((value) => !value)}
            className="inline-flex items-center justify-center rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-gray-300 hover:bg-white/5"
          >
            {isDetailed ? '간략 보기' : '상세 보기'}
          </button>
        )}
      </div>
      {problems.length > 0 ? (
        <div className="divide-y divide-white/5">
          {visibleProblems.map((problem) => (
            <div key={`${problem.problemId}-${problem.solvedAt}`} className="first:pt-0 last:pb-0">
              {isDetailed ? (
                <div className="flex flex-col gap-3 py-4 md:flex-row md:items-start md:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="inline-flex h-7 w-[72px] items-center justify-center rounded-lg border border-blue-400/20 bg-blue-400/10 text-[11px] font-bold tabular-nums text-blue-300">
                        {problem.problemId}
                      </span>
                      <span className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[11px] text-gray-300">
                        {problem.tierName || 'Unknown'}
                      </span>
                      <span className="text-[11px] text-gray-500">{problem.solvedAt || '-'}</span>
                    </div>
                    <div className="mt-2 min-w-0 break-words text-sm font-semibold text-gray-100">{problem.title}</div>
                    {problem.tags && problem.tags.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {problem.tags.slice(0, 5).map((tag) => (
                          <span key={`${problem.problemId}-${tag}`} className="rounded-full bg-purple-500/10 px-2 py-0.5 text-[11px] text-purple-200">
                            #{tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => onOpenProblem(problem.problemId)}
                    className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-xs text-gray-300 hover:bg-white/5"
                  >
                    <FileCode2 className="h-4 w-4" />
                    문제 열기
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-[72px_minmax(0,1fr)_40px] items-center gap-3 py-3 sm:grid-cols-[76px_minmax(0,1fr)_92px_44px]">
                  <span className="inline-flex h-8 w-[72px] items-center justify-center rounded-xl border border-blue-400/25 bg-blue-400/10 text-xs font-bold tabular-nums text-blue-200">
                    {problem.problemId}
                  </span>
                  <div className="min-w-0 truncate text-sm font-semibold text-gray-100">{problem.title}</div>
                  <div className="hidden truncate text-right text-xs text-gray-400 sm:block">{problem.tierName || 'Unknown'}</div>
                  <button
                    type="button"
                    onClick={() => onOpenProblem(problem.problemId)}
                    className="inline-flex shrink-0 items-center justify-center rounded-xl border border-white/10 px-3 py-2 text-xs text-gray-300 hover:bg-white/5"
                  >
                    <FileCode2 className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="flex min-h-36 items-center justify-center rounded-xl border border-dashed border-gray-800 text-sm text-gray-500">
          최근 풀이 기록이 없습니다
        </div>
      )}
    </div>
  );
}
