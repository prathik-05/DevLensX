import React from 'react';

interface SkeletonProps {
  variant?: 'text' | 'title' | 'card' | 'avatar' | 'badge' | 'table-row' | 'wiki-section' | 'codemap-stop';
  lines?: number;
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'text',
  lines = 1,
  className = '',
}) => {
  const variants = {
    text: 'dl-skeleton-text',
    title: 'dl-skeleton-title',
    card: 'dl-skeleton-card',
    avatar: 'dl-skeleton-avatar',
    badge: 'dl-skeleton-badge',
    'table-row': 'h-10 w-full',
    'wiki-section': 'dl-skeleton h-32 w-full',
    'codemap-stop': 'dl-skeleton h-24 w-full',
  };

  if (variant === 'text' && lines > 1) {
    return (
      <div className={`space-y-2 ${className}`}>
        {Array.from({ length: lines }).map((_, i) => (
          <div key={i} className={`${variants.text} ${i === lines - 1 ? 'w-3/4' : ''}`} />
        ))}
      </div>
    );
  }

  return <div className={`${variants[variant]} dl-skeleton ${className}`} />;
};

export const CardSkeleton: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`glass-raised rounded-xl p-6 space-y-4 ${className}`}>
    <div className="flex items-center justify-between">
      <Skeleton variant="title" />
      <Skeleton variant="badge" />
    </div>
    <Skeleton variant="text" lines={3} />
    <div className="flex gap-2">
      <Skeleton variant="badge" />
      <Skeleton variant="badge" />
      <Skeleton variant="badge" />
    </div>
  </div>
);

export const WikiSectionSkeleton: React.FC<{ className?: string }> = ({ className = '' }) => (
  <section className={`glass-raised rounded-xl p-6 space-y-4 ${className}`}>
    <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: 'var(--glass-surface-border)' }}>
      <Skeleton variant="title" className="w-1/3" />
      <Skeleton variant="badge" />
    </div>
    <Skeleton variant="text" lines={4} />
  </section>
);

export const CodemapStopSkeleton: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`glass-raised rounded-xl p-4 space-y-3 ${className}`}>
    <div className="flex items-center justify-between">
      <Skeleton variant="title" className="w-1/2" />
      <Skeleton variant="text" className="w-24" />
    </div>
    <Skeleton variant="text" lines={2} />
    <div className="h-1.5 w-full rounded-full glass-surface" />
  </div>
);

export const TableRowSkeleton: React.FC<{ columns?: number; className?: string }> = ({
  columns = 4,
  className = '',
}) => (
  <div className={`flex items-center gap-4 p-3 ${className}`}>
    <Skeleton variant="avatar" />
    <div className="flex-1 space-y-1.5">
      {Array.from({ length: columns - 1 }).map((_, i) => (
        <Skeleton key={i} variant="text" className={i === 0 ? 'w-1/3' : 'w-1/4'} />
      ))}
    </div>
  </div>
);

export const PageSkeleton: React.FC<{ sections?: number; className?: string }> = ({
  sections = 3,
  className = '',
}) => (
  <div className={`space-y-6 ${className}`}>
    <div className="flex items-center justify-between">
      <Skeleton variant="title" className="w-1/3" />
      <Skeleton variant="badge" />
    </div>
    {Array.from({ length: sections }).map((_, i) => (
      <WikiSectionSkeleton key={i} />
    ))}
  </div>
);