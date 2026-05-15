import { FileCode2 } from 'lucide-react';
import type { LocalSolvedProblem } from '../../types/dashboard';

interface RecentSolvedListProps {
  problems: LocalSolvedProblem[];
  onOpenProblem: (problemId: number | string) => void;
}

export function RecentSolvedList({ problems, onOpenProblem }: RecentSolvedListProps) {
  return (
    <div className="rounded-2xl border border-gray-800 bg-[#1E1F20] p-5">
      <div className="mb-4">
        <h3 className="text-sm font-bold text-white">최근 푼 문제</h3>
        <p className="mt-1 text-xs text-gray-500">로컬 solved 로그 최신순</p>
      </div>
      {problems.length > 0 ? (
        <div className="divide-y divide-white/5">
          {problems.map((problem) => (
            <div key={`${problem.problemId}-${problem.solvedAt}`} className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 md:flex-row md:items-start md:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-lg border border-blue-400/20 bg-blue-400/10 px-2 py-1 text-[11px] font-bold text-blue-300">
                    {problem.problemId}
                  </span>
                  <span className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[11px] text-gray-300">
                    {problem.tierName || 'Unknown'}
                  </span>
                  <span className="text-[11px] text-gray-500">{problem.solvedAt || '-'}</span>
                </div>
                <div className="mt-2 break-words text-sm font-semibold text-gray-100">{problem.title}</div>
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
