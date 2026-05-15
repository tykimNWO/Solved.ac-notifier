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

export interface RatingProblem {
  problemId: number | string;
  title?: string;
  level: number;
  tierName?: string;
  tags?: string[];
  solvedAt?: string;
  isSolved?: boolean;
  isExtra?: boolean;
  isUnrated?: boolean;
}

export interface ClassProgress {
  classLevel: number;
  requiredSolvedCount: number;
  solvedCount: number;
  totalProblems: number;
  essentialProblems: number;
  achieved: boolean;
}

export interface RatingBreakdown {
  topProblemScore: number;
  classBonus: number;
  solvedCountBonus: number;
  contributionBonus: number;
  total: number;
  solvedCountForRating: number;
  topProblems: RatingProblem[];
  localClassLevel: number;
  classStatus?: string;
  classProgress?: ClassProgress[];
}

export interface TagRatingBreakdown {
  tag: string;
  rating: number;
  topProblemScore: number;
  solvedCountBonus: number;
  solvedCount: number;
  topProblems: RatingProblem[];
}

export interface LocalRatingResult {
  acRating: RatingBreakdown;
  tagRatings: TagRatingBreakdown[];
}

export interface ClassProblemGroup {
  classLevel: number;
  requiredSolvedCount: number;
  totalProblems: number;
  essentialProblems: number;
  problems: Array<{
    problemId: number | string;
    title?: string;
    isEssential?: boolean;
  }>;
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
  }>;
  localRating?: LocalRatingResult;
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
