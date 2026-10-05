import React from 'react';
import { VERDICT_META, type Verdict } from '../evidence';

export type BadgeVariant =
  | 'verified'
  | 'ai-suggestion'
  | 'insufficient'
  | 'not-verified'
  | 'risk-critical'
  | 'risk-high'
  | 'risk-medium'
  | 'risk-low'
  | 'finding-arch'
  | 'finding-sec'
  | 'finding-impact'
  | 'finding-perf';

export type BadgeSize = 'sm' | 'md' | 'lg';

const variantClassMap: Record<BadgeVariant, string> = {
  verified: 'dl-badge-verified',
  'ai-suggestion': 'dl-badge-ai-suggestion',
  insufficient: 'dl-badge-insufficient',
  'not-verified': 'dl-badge-not-verified',
  'risk-critical': 'dl-badge-risk-critical',
  'risk-high': 'dl-badge-risk-high',
  'risk-medium': 'dl-badge-risk-medium',
  'risk-low': 'dl-badge-risk-low',
  'finding-arch': 'dl-badge-arch',
  'finding-sec': 'dl-badge-sec',
  'finding-impact': 'dl-badge-impact',
  'finding-perf': 'dl-badge-perf',
};

const sizeClassMap: Record<BadgeSize, string> = {
  sm: 'px-2 py-0.5 text-[9px] gap-1.5',
  md: 'px-2.5 py-1 text-[10px] gap-2',
  lg: 'px-3 py-1.5 text-[11px] gap-2',
};

interface BadgeProps {
  variant: BadgeVariant;
  children: React.ReactNode;
  size?: BadgeSize;
  icon?: React.ReactNode;
  className?: string;
  title?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  variant,
  children,
  size = 'md',
  icon,
  className = '',
  title,
}) => (
  <span
    className={`dl-badge ${variantClassMap[variant]} ${sizeClassMap[size]} ${className}`}
    title={title}
  >
    {icon}
    <span>{children}</span>
  </span>
);

export const VerificationBadge: React.FC<{
  verdict: Verdict;
  size?: BadgeSize;
  compact?: boolean;
  className?: string;
}> = ({ verdict, size = 'md', compact = false, className = '' }) => {
  const meta = VERDICT_META[verdict] ?? VERDICT_META.NOT_VERIFIED;
  const variantMap: Record<Verdict, BadgeVariant> = {
    VERIFIED: 'verified',
    AI_SUGGESTION: 'ai-suggestion',
    INSUFFICIENT_EVIDENCE: 'insufficient',
    NOT_VERIFIED: 'not-verified',
  };
  return (
    <Badge
      variant={variantMap[verdict]}
      size={size}
      icon={<span aria-hidden>{meta.emoji}</span>}
      className={className}
      title={meta.label}
    >
      {!compact && meta.label}
    </Badge>
  );
};

export const RiskBadge: React.FC<{
  level: 'critical' | 'high' | 'medium' | 'low';
  size?: BadgeSize;
  className?: string;
}> = ({ level, size = 'md', className = '' }) => {
  const labelMap = { critical: 'CRITICAL', high: 'HIGH', medium: 'MEDIUM', low: 'LOW' };
  return (
    <Badge variant={`risk-${level}` as BadgeVariant} size={size} className={className}>
      {labelMap[level]}
    </Badge>
  );
};

export const FindingCategoryBadge: React.FC<{
  category: 'architectural' | 'security' | 'impact' | 'performance';
  size?: BadgeSize;
  className?: string;
}> = ({ category, size = 'md', className = '' }) => {
  const variantMap = {
    architectural: 'finding-arch',
    security: 'finding-sec',
    impact: 'finding-impact',
    performance: 'finding-perf',
  } as const;
  const labelMap = { architectural: 'ARCH', security: 'SEC', impact: 'IMPACT', performance: 'PERF' };
  return (
    <Badge variant={variantMap[category]} size={size} className={className}>
      {labelMap[category]}
    </Badge>
  );
};

export const StatusBadge: React.FC<{
  status: 'online' | 'offline' | 'degraded' | 'maintenance' | 'analyzing' | 'complete' | 'error';
  size?: BadgeSize;
  className?: string;
}> = ({ status, size = 'md', className = '' }) => {
  const variantMap = {
    online: 'verified',
    offline: 'not-verified',
    degraded: 'risk-medium',
    maintenance: 'finding-perf',
    analyzing: 'ai-suggestion',
    complete: 'verified',
    error: 'risk-high',
  } as const;
  return <Badge variant={variantMap[status]} size={size} className={className}>{status.toUpperCase()}</Badge>;
};