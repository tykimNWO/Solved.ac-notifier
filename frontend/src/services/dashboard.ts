import type { DashboardResponse } from '../types/dashboard';

const API_BASE_URL = 'http://localhost:8000/api';

export const fetchDashboard = async (): Promise<DashboardResponse> => {
  const response = await fetch(`${API_BASE_URL}/dashboard`);
  if (!response.ok) {
    throw new Error('대시보드 데이터를 불러오지 못했습니다.');
  }
  return response.json();
};
