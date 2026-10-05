import React from 'react';
import type { CSSProperties } from 'react';

export type GlassElevation = 'surface' | 'raised' | 'overlay' | 'modal';

interface GlassPanelProps {
  elevation?: GlassElevation;
  children: React.ReactNode;
  className?: string;
  style?: CSSProperties;
  padding?: 'none' | 'sm' | 'md' | 'lg' | 'xl';
  radius?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  hover?: boolean;
  cornerShape?: 'circle' | 'square' | 'triangle' | 'none';
  cornerColor?: 'red' | 'blue' | 'yellow' | 'green' | 'cyan' | 'magenta';
  chamfer?: boolean;
  accentBorder?: 'green' | 'cyan' | 'magenta' | 'yellow' | 'red' | 'none';
  onClick?: () => void;
}

const paddingMap = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
  xl: 'p-8',
};

const elevationClassMap: Record<GlassElevation, string> = {
  surface: 'bg-white dark:bg-[#121316] border border-black dark:border-[#26272e] shadow-[3px_3px_0px_0px_#000000] dark:shadow-none text-[#0f172a] dark:text-[#f4f4f5]',
  raised: 'bg-white dark:bg-[#141519] border border-black dark:border-[#26272e] shadow-[4px_4px_0px_0px_#000000] dark:shadow-none text-[#0f172a] dark:text-[#f4f4f5]',
  overlay: 'bg-[#fafafa] dark:bg-[#18191e] border border-black dark:border-[#2b2c34] shadow-[6px_6px_0px_0px_#000000] dark:shadow-none text-[#0f172a] dark:text-[#f4f4f5]',
  modal: 'bg-white dark:bg-[#1c1d23] border border-black dark:border-[#32333b] shadow-[8px_8px_0px_0px_#000000] dark:shadow-none text-[#0f172a] dark:text-[#f4f4f5]',
};

export const GlassPanel: React.FC<GlassPanelProps> = ({
  elevation = 'raised',
  children,
  className = '',
  style,
  padding = 'md',
  radius = 'none',
  hover = false,
  cornerShape = 'none',
  cornerColor = 'green',
  chamfer = false,
  accentBorder = 'none',
  onClick,
}) => {
  const baseClasses = elevationClassMap[elevation];
  const paddingClass = paddingMap[padding];
  const radiusClass = radius === 'full' ? 'rounded-full' : (chamfer ? 'cyber-chamfer' : 'rounded-none');
  const hoverClass = hover ? 'transition-all duration-150 ease-out hover:-translate-y-0.5 hover:shadow-[6px_6px_0px_0px_#000000] dark:hover:border-zinc-600 cursor-pointer' : '';

  const accentBorderMap = {
    none: '',
    green: '!border-[#059669] hover:shadow-[4px_4px_0px_0px_#059669]',
    cyan: '!border-[#0284c7] hover:shadow-[4px_4px_0px_0px_#0284c7]',
    magenta: '!border-[#c026d3] hover:shadow-[4px_4px_0px_0px_#c026d3]',
    yellow: '!border-[#d97706] hover:shadow-[4px_4px_0px_0px_#d97706]',
    red: '!border-[#dc2626] hover:shadow-[4px_4px_0px_0px_#dc2626]',
  };

  const colorBgMap: Record<string, string> = {
    red: 'bg-[#dc2626]',
    blue: 'bg-[#2563eb]',
    yellow: 'bg-[#d97706]',
    green: 'bg-[#059669]',
    cyan: 'bg-[#0284c7]',
    magenta: 'bg-[#c026d3]',
  };

  return (
    <div
      className={`relative ${baseClasses} ${radiusClass} ${paddingClass} ${hoverClass} ${accentBorderMap[accentBorder]} ${className}`}
      style={style}
      onClick={onClick}
    >
      {/* Bauhaus Geometric Corner Emblem */}
      {cornerShape !== 'none' && (
        <div className="absolute top-2.5 right-2.5 flex items-center gap-1 z-10 pointer-events-none">
          {cornerShape === 'circle' && (
            <div className={`w-3 h-3 rounded-full ${colorBgMap[cornerColor] || 'bg-[#00d4ff]'} border border-black shadow-[1px_1px_0px_#000]`} />
          )}
          {cornerShape === 'square' && (
            <div className={`w-3 h-3 rounded-none ${colorBgMap[cornerColor] || 'bg-[#ff00ff]'} border border-black shadow-[1px_1px_0px_#000]`} />
          )}
          {cornerShape === 'triangle' && (
            <div
              className={`w-3 h-3 ${colorBgMap[cornerColor] || 'bg-[#f0c020]'} border border-black`}
              style={{ clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)' }}
            />
          )}
        </div>
      )}

      {children}
    </div>
  );
};

export const GlassCard = ({ children, className = '', ...props }: Omit<GlassPanelProps, 'elevation'>) => (
  <GlassPanel elevation="raised" className={className} {...props}>{children}</GlassPanel>
);

export const GlassSurface = ({ children, className = '', ...props }: Omit<GlassPanelProps, 'elevation'>) => (
  <GlassPanel elevation="surface" className={className} {...props}>{children}</GlassPanel>
);

export const GlassOverlay = ({ children, className = '', ...props }: Omit<GlassPanelProps, 'elevation'>) => (
  <GlassPanel elevation="overlay" className={className} {...props}>{children}</GlassPanel>
);

export const GlassModal = ({ children, className = '', ...props }: Omit<GlassPanelProps, 'elevation'>) => (
  <GlassPanel elevation="modal" className={className} {...props}>{children}</GlassPanel>
);