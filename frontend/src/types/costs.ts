export interface CostSummary {
  mtd_cost: number;
  mtd_forecast: number;
  last_month_cost: number;
  ytd_cost: number;
  currency: string;
  period_start: string;
  period_end: string;
}

export interface CostByService {
  service: string;
  cost: number;
  percentage: number;
}

export interface CostByRegion {
  region: string;
  cost: number;
  percentage: number;
}

export interface CostBreakdown {
  by_service: CostByService[];
  by_region: CostByRegion[];
  total: number;
  currency: string;
  period_start: string;
  period_end: string;
}

export interface CostForecast {
  forecasted_cost: number;
  confidence_level: number;
  period_start: string;
  period_end: string;
  currency: string;
}

export interface CostRecommendation {
  resource_id: string;
  resource_type: string;
  recommendation_type: string;
  description: string;
  estimated_monthly_savings: number;
  current_monthly_cost: number;
  priority: 'high' | 'medium' | 'low';
}

export interface CostRecommendationsResponse {
  recommendations: CostRecommendation[];
  total_potential_savings: number;
  currency: string;
}

export interface DailyCost {
  date: string;
  cost: number;
}
