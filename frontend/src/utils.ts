import type { HealthLabel, Lifecycle } from './types';

export const HEALTH_COLORS: Record<HealthLabel, string> = {
  healthy: '#22c55e',
  warning: '#eab308',
  abnormal: '#f97316',
  danger: '#ef4444',
};

export const HEALTH_LABELS_CN: Record<HealthLabel, string> = {
  healthy: '健康',
  warning: '预警',
  abnormal: '异常',
  danger: '危险',
};

export const LIFECYCLE_CN: Record<Lifecycle, string> = {
  new: '新品期',
  growth: '成长期',
  mature: '成熟期',
  decline: '衰退期',
};

export const DIMENSION_CN: Record<string, string> = {
  sales: '销量',
  inventory: '库存',
  advertising: '广告',
  after_sales: '售后',
  profitability: '盈利性',
  listing: 'Listing质量',
};

export function healthLabelEmoji(label: HealthLabel): string {
  const map: Record<HealthLabel, string> = {
    healthy: '\u{1F7E2}',
    warning: '\u{1F7E1}',
    abnormal: '\u{1F7E0}',
    danger: '\u{1F534}',
  };
  return map[label];
}
