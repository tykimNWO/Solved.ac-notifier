import { useEffect, useRef, useState } from 'react';
import { AlertCircle, Loader2, RefreshCw } from 'lucide-react';
import { fetchDashboard } from '../../services/dashboard';
import type { DashboardResponse } from '../../types/dashboard';
import { DifficultyChart } from './DifficultyChart';
import { LocalRatingSummaryCard } from './LocalRatingSummaryCard';
import { ProfileSummaryCard } from './ProfileSummaryCard';
import { RatingBreakdownCard } from './RatingBreakdownCard';
import { RecentSolvedList } from './RecentSolvedList';
import { SolvedTrendChart } from './SolvedTrendChart';
import { StatsCards } from './StatsCards';
import { TagChart } from './TagChart';

interface DashboardProps {
  onOpenProblem: (problemId: number | string) => void;
  onReady?: () => void;
}

export function Dashboard({ onOpenProblem, onReady }: DashboardProps) {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const shouldNotifyReadyRef = useRef(true);

  const loadDashboard = async (options?: { restoreOnReady?: boolean }) => {
    shouldNotifyReadyRef.current = options?.restoreOnReady ?? false;
    setIsLoading(true);
    setError('');
    try {
      const data = await fetchDashboard();
      setDashboard(data);
    } catch (err) {
      console.error('대시보드 로드 실패:', err);
      setError('대시보드 데이터를 불러오지 못했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard({ restoreOnReady: true });
  }, []);

  useEffect(() => {
    if (!isLoading && dashboard && shouldNotifyReadyRef.current) {
      shouldNotifyReadyRef.current = false;
      onReady?.();
    }
  }, [dashboard, isLoading, onReady]);

  if (isLoading && !dashboard) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex items-center gap-3 text-sm text-gray-400">
          <Loader2 className="h-5 w-5 animate-spin text-blue-400" />
          대시보드 데이터를 불러오는 중...
        </div>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-2xl items-center justify-center p-6">
        <div className="w-full rounded-2xl border border-red-500/20 bg-red-500/5 p-6 text-center">
          <AlertCircle className="mx-auto h-6 w-6 text-red-300" />
          <h2 className="mt-3 text-lg font-bold text-white">대시보드를 표시하지 못했습니다</h2>
          <p className="mt-2 text-sm text-gray-400">{error || '잠시 후 다시 시도해 주세요.'}</p>
          <button
            type="button"
            onClick={() => loadDashboard({ restoreOnReady: true })}
            className="mt-5 inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 px-4 py-2 text-xs font-semibold text-gray-200 hover:bg-white/5"
          >
            <RefreshCw className="h-4 w-4" />
            다시 불러오기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-6xl p-6 pb-28">
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-purple-400 to-purple-600">
            코딩 대시보드
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            {dashboard.handle}님의 solved.ac / 로컬 풀이 기록 기반 성장 현황
          </p>
        </div>
        <button
          type="button"
          onClick={() => loadDashboard()}
          disabled={isLoading}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 px-4 py-2 text-xs font-semibold text-gray-300 hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          {isLoading ? '새로고침 중' : '새로고침'}
        </button>
      </div>

      {dashboard.warnings && dashboard.warnings.length > 0 && (
        <div className="mb-5 space-y-2">
          {dashboard.warnings.map((warning) => (
            <div key={warning} className="flex items-start gap-2 rounded-xl border border-yellow-500/20 bg-yellow-500/5 px-4 py-3 text-xs text-yellow-100">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-yellow-300" />
              <span>{warning}</span>
            </div>
          ))}
        </div>
      )}

      <div className="space-y-5">
        <ProfileSummaryCard profile={dashboard.profile} />
        <LocalRatingSummaryCard localRating={dashboard.stats.localRating} profile={dashboard.profile} />
        <RatingBreakdownCard localRating={dashboard.stats.localRating} />
        <StatsCards stats={dashboard.stats} />
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <DifficultyChart data={dashboard.stats.difficultyDistribution} totalSolved={dashboard.stats.totalSolved} />
          <TagChart data={dashboard.stats.localRating?.tagRatings} totalSolved={dashboard.stats.totalSolved} />
          <SolvedTrendChart data={dashboard.stats.dailySolvedTrend} />
        </div>
        <RecentSolvedList problems={dashboard.stats.recentProblems} onOpenProblem={onOpenProblem} />
      </div>
    </div>
  );
}
