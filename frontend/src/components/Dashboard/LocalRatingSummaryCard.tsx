import { Activity, Scale } from 'lucide-react';
import type { LocalRatingResult, SolvedAcProfileSnapshot } from '../../types/dashboard';

interface LocalRatingSummaryCardProps {
  localRating?: LocalRatingResult;
  profile?: SolvedAcProfileSnapshot | null;
}

const formatNumber = (value?: number | null) =>
  typeof value === 'number' ? value.toLocaleString() : '-';

export function LocalRatingSummaryCard({ localRating, profile }: LocalRatingSummaryCardProps) {
  const localTotal = localRating?.acRating.total ?? 0;
  const officialRating = profile?.rating;
  const diff = typeof officialRating === 'number' ? localTotal - officialRating : null;

  return (
    <div className="rounded-2xl border border-blue-500/20 bg-[#091216] p-5">
      <div className="mb-5 flex items-center gap-2 text-sm font-semibold text-blue-300">
        <Activity className="h-4 w-4" />
        Local Rating
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-white/10 bg-black/20 p-4">
          <div className="text-xs text-gray-500">Local AC Rating</div>
          <div className="mt-2 text-3xl font-bold text-white">{formatNumber(localTotal)}</div>
          <p className="mt-2 text-xs text-gray-500">sqlite solved 로그 기준 추정값</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/20 p-4">
          <div className="text-xs text-gray-500">Official solved.ac Rating</div>
          <div className="mt-2 text-3xl font-bold text-gray-100">{formatNumber(officialRating)}</div>
          <p className="mt-2 text-xs text-gray-500">캐시된 공식 프로필 snapshot</p>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/20 p-4">
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Scale className="h-3.5 w-3.5" />
            Difference
          </div>
          <div className={`mt-2 text-3xl font-bold ${diff === null ? 'text-gray-100' : diff >= 0 ? 'text-green-300' : 'text-yellow-300'}`}>
            {diff === null ? '-' : `${diff >= 0 ? '+' : ''}${diff.toLocaleString()}`}
          </div>
          <p className="mt-2 text-xs leading-relaxed text-gray-500">
            공식 rating과 Local Rating은 데이터 기준과 CLASS 처리 방식이 달라 차이가 날 수 있습니다.
          </p>
        </div>
      </div>
    </div>
  );
}
