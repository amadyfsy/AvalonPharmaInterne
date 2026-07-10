import {
  DEFAULT_LOGO,
  DEFAULT_LOGO_HORIZONTAL,
  BRAND_NAME,
} from '../config/brand';

interface BrandLogoProps {
  alt?: string;
  className?: string;
  variant?: 'header' | 'hero' | 'footer';
}

/** Logo du site public — assets locaux uniquement (indépendant de l’ERP). */
const LOGO_BY_VARIANT = {
  header: DEFAULT_LOGO_HORIZONTAL,
  hero: DEFAULT_LOGO,
  footer: DEFAULT_LOGO_HORIZONTAL,
} as const;

export default function BrandLogo({
  alt = BRAND_NAME,
  className = '',
  variant = 'header',
}: BrandLogoProps) {
  return (
    <img
      src={LOGO_BY_VARIANT[variant]}
      alt={alt}
      className={`brand-logo brand-logo--${variant} ${className}`.trim()}
      loading={variant === 'hero' ? 'eager' : 'lazy'}
    />
  );
}
