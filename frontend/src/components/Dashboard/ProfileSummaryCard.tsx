import { AlertCircle, Trophy } from 'lucide-react';
import type { SolvedAcProfileSnapshot } from '../../types/dashboard';

const formatNumber = (value?: number | null) =>
  typeof value === 'number' ? value.toLocaleString() : '-';

const getTierName = (tier?: number | string | null) => {
  if (typeof tier === 'string') return tier || '-';
  if (!tier || tier <= 0) return 'Unrated';
  if (tier <= 5) return `Bronze ${6 - tier}`;
  if (tier <= 10) return `Silver ${11 - tier}`;
  if (tier <= 15) return `Gold ${16 - tier}`;
  if (tier <= 20) return `Platinum ${21 - tier}`;
  if (tier <= 25) return `Diamond ${26 - tier}`;
  return `Ruby ${31 - tier}`;
};

interface ProfileSummaryCardProps {
  profile?: SolvedAcProfileSnapshot | null;
}

export function ProfileSummaryCard({ profile }: ProfileSummaryCardProps) {
  if (!profile) {
    return (
      <div className="rounded-2xl border border-yellow-500/20 bg-yellow-500/5 p-5">
        <div className="flex items-center gap-2 text-sm font-semibold text-yellow-300">
          <AlertCircle className="h-4 w-4" />
          Rating 정보를 불러오지 못했습니다
        </div>
        <p className="mt-2 text-xs leading-relaxed text-gray-400">
          로컬 풀이 기록 기반 통계는 계속 표시됩니다.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-blue-500/20 bg-[#1E1F20] p-5 shadow-lg shadow-black/10">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-blue-300">
            <Trophy className="h-4 w-4" />
            solved.ac Profile
          </div>
          <h2 className="mt-2 text-2xl font-bold text-white">{profile.handle}</h2>
          <p className="mt-1 text-xs text-gray-500">
            {profile.source === 'sqlite_cache' ? '캐시된 프로필' : profile.source === 'user_stats_fallback' ? '로컬 스냅샷' : '공식 프로필'} · {profile.fetchedAt || '-'}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 md:min-w-[480px]">
          <div className="rounded-xl border border-white/5 bg-black/20 p-3">
            <div className="text-[11px] text-gray-500">Tier</div>
            <div className="mt-1 text-sm font-bold text-gray-100">{getTierName(profile.tier)}</div>
          </div>
          <div className="rounded-xl border border-white/5 bg-black/20 p-3">
            <div className="text-[11px] text-gray-500">AC Rating</div>
            <div className="mt-1 text-sm font-bold text-gray-100">{formatNumber(profile.rating)}</div>
          </div>
          <div className="rounded-xl border border-white/5 bg-black/20 p-3">
            <div className="text-[11px] text-gray-500">Class</div>
            <div className="mt-1 text-sm font-bold text-gray-100">{formatNumber(profile.class)}</div>
          </div>
          <div className="rounded-xl border border-white/5 bg-black/20 p-3">
            <div className="text-[11px] text-gray-500">Official Solved</div>
            <div className="mt-1 text-sm font-bold text-gray-100">{formatNumber(profile.solvedCount)}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
