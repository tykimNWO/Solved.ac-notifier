import { BarChart3, CalendarDays, Flame, ListChecks, Sigma } from 'lucide-react';
import type { DashboardStats } from '../../types/dashboard';

const formatNumber = (value?: number | null) =>
  typeof value === 'number' ? value.toLocaleString() : '-';

interface StatsCardsProps {
  stats: DashboardStats;
}

export function StatsCards({ stats }: StatsCardsProps) {
  const cards = [
    {
      label: 'Total Solved',
      value: formatNumber(stats.totalSolved),
      icon: ListChecks,
      tone: 'text-blue-300',
    },
    {
      label: 'Current Streak',
      value: `${formatNumber(stats.currentStreak)}일`,
      icon: Flame,
      tone: 'text-orange-300',
    },
    {
      label: 'Longest Streak',
      value: `${formatNumber(stats.longestStreak)}일`,
      icon: CalendarDays,
      tone: 'text-green-300',
    },
    {
      label: 'Last 7 Days',
      value: formatNumber(stats.solvedLast7Days),
      icon: BarChart3,
      tone: 'text-purple-300',
    },
    {
      label: 'Last 30 Days',
      value: formatNumber(stats.solvedLast30Days),
      icon: BarChart3,
      tone: 'text-cyan-300',
    },
    {
      label: 'Average Level',
      value: stats.averageLevel ? stats.averageLevel.toFixed(1) : '-',
      icon: Sigma,
      tone: 'text-yellow-300',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div key={card.label} className="rounded-2xl border border-gray-800 bg-[#1E1F20] p-4">
            <div className={`mb-3 inline-flex rounded-xl bg-white/5 p-2 ${card.tone}`}>
              <Icon className="h-4 w-4" />
            </div>
            <div className="text-[11px] font-medium text-gray-500">{card.label}</div>
            <div className="mt-1 text-xl font-bold text-white">{card.value}</div>
          </div>
        );
      })}
    </div>
  );
}
