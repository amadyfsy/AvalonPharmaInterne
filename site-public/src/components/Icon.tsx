import type { LucideIcon } from 'lucide-react';

export interface IconProps {
  icon: LucideIcon;
  size?: number;
  strokeWidth?: number;
  className?: string;
  label?: string;
}

/** Icône SVG Lucide — la couleur suit `color` / `currentColor` du parent. */
export default function Icon({
  icon: IconComponent,
  size = 24,
  strokeWidth = 1.75,
  className = '',
  label,
}: IconProps) {
  return (
    <IconComponent
      size={size}
      strokeWidth={strokeWidth}
      className={`ui-icon ${className}`.trim()}
      aria-hidden={label ? undefined : true}
      aria-label={label}
      role={label ? 'img' : undefined}
    />
  );
}
