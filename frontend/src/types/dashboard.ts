export interface SolvedAcProfileSnapshot {
  handle: string;
  tier?: number | string | null;
  rating?: number | null;
  class?: number | null;
  solvedCount?: number | null;
  rank?: number | null;
  fetchedAt: string;
  source?: 'solved_ac_api' | 'sqlite_cache' | 'user_stats_fallback';
}

export interface LocalSolvedProblem {
  problemId: number | string;
  title: string;
  level?: number | null;
  tierName?: string;
  tags?: string[];
  solvedAt: string;
  source?: 'sqlite' | 'manual' | 'solved_ac';
  bojUrl?: string;
  solvedAcUrl?: string;
}

export interface DashboardStats {
  totalSolved: number;
  currentStreak: number;
  longestStreak: number;
  solvedLast7Days: number;
  solvedLast30Days: number;
  averageLevel?: number | null;
  difficultyDistribution: Array<{
    tier: string;
    level?: number;
    count: number;
  }>;
  tagDistribution: Array<{
    tag: string;
    count: number;
    percent?: number;
    rating?: number;
    rank?: number;
  }>;
  recentProblems: LocalSolvedProblem[];
  dailySolvedTrend?: Array<{
    date: string;
    count: number;
  }>;
}

export interface DashboardResponse {
  status: 'success' | 'error';
  handle: string;
  profile?: SolvedAcProfileSnapshot | null;
  stats: DashboardStats;
  warnings?: string[];
}
