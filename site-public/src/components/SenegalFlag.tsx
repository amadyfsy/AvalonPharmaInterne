interface SenegalFlagProps {
  className?: string;
  title?: string;
}

/** Drapeau du Sénégal — SVG vectoriel (couleurs officielles). */
export default function SenegalFlag({
  className = '',
  title = 'Drapeau du Sénégal',
}: SenegalFlagProps) {
  return (
    <svg
      className={`senegal-flag ${className}`.trim()}
      viewBox="0 0 90 60"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label={title}
    >
      <title>{title}</title>
      <rect width="30" height="60" fill="#00853F" />
      <rect x="30" width="30" height="60" fill="#FDEF42" />
      <rect x="60" width="30" height="60" fill="#E31B23" />
      <path
        fill="#00853F"
        d="M45 18.5l2.35 7.23h7.6l-6.15 4.47 2.35 7.23L45 33l-6.15 4.43 2.35-7.23-6.15-4.47h7.6z"
      />
    </svg>
  );
}
