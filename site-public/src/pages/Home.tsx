import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import BrandLogo from '../components/BrandLogo';
import Icon from '../components/Icon';
import { PILLAR_ICON_MAP, SPECIALITE_ICONS, VALUE_ICON_MAP } from '../icons/medical';
import type { Entreprise } from '../types';

const PILLARS = [
  {
    num: '01',
    title: 'Médicaments & solutions',
    text: 'Spécialités pharmaceutiques et solutions thérapeutiques pour hôpitaux, cliniques et cabinets.',
  },
  {
    num: '02',
    title: 'Dispositifs médicaux',
    text: 'Consommables, implants et instrumentation pour la chirurgie, l’ophtalmologie et l’orthopédie.',
  },
  {
    num: '03',
    title: 'Équipement biomédical',
    text: 'Matériel d’imagerie, de laboratoire, de bloc opératoire et de stérilisation.',
  },
  {
    num: '04',
    title: 'Accompagnement expert',
    text: 'Logistique fiable, conseil technique et suivi personnalisé de vos approvisionnements.',
  },
];

const VALUES = [
  { title: 'Qualité certifiée', desc: 'Produits conformes aux normes internationales.' },
  { title: 'Réactivité', desc: 'Délais maîtrisés et disponibilité des stocks.' },
  { title: 'Expertise médicale', desc: 'Une équipe qui comprend vos spécialités.' },
  { title: 'Couverture nationale', desc: 'Livraison sur tout le territoire sénégalais.' },
];

interface HomeProps {
  entreprise: Entreprise;
}

export default function Home({ entreprise }: HomeProps) {
  return (
    <>
      <section className="hero">
        <div className="hero-bg" aria-hidden="true">
          <div className="hero-pyramid" />
          <div className="hero-glow" />
        </div>
        <div className="container hero-grid">
          <div className="hero-content">
            <span className="hero-eyebrow">Distribution pharmaceutique · Sénégal</span>
            <h1>
              L&apos;excellence au service
              <span className="hero-highlight"> des soignants</span>
            </h1>
            <p className="hero-lead">
              <strong>{entreprise.raison_sociale}</strong> — {entreprise.slogan}. Nous équipons les
              établissements de santé avec un catalogue complet : de l&apos;ophtalmologie à la
              gynécologie, du bloc opératoire au laboratoire.
            </p>
            <div className="hero-actions">
              <Link to="/catalogue" className="btn btn-primary btn-lg">
                Découvrir le catalogue
              </Link>
              <a href="#specialites" className="btn btn-ghost btn-lg">
                Par spécialité
              </a>
            </div>
            <div className="hero-trust">
              {VALUES.map((v) => (
                <div key={v.title} className="hero-trust-item">
                  <span className="hero-trust-icon">
                    <Icon icon={VALUE_ICON_MAP[v.title]} size={20} />
                  </span>
                  <div>
                    <strong>{v.title}</strong>
                    <span>{v.desc}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="hero-visual">
            <div className="hero-logo-frame">
              <BrandLogo alt={entreprise.raison_sociale} variant="hero" />
            </div>
            <div className="hero-stats">
              <div className="hero-stat-card">
                <span className="hero-stat-num">500+</span>
                <span className="hero-stat-label">Références</span>
              </div>
              <div className="hero-stat-card">
                <span className="hero-stat-num">15+</span>
                <span className="hero-stat-label">Spécialités</span>
              </div>
              <div className="hero-stat-card accent">
                <span className="hero-stat-num">SN</span>
                <span className="hero-stat-label">National</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="about" className="section about-strip">
        <div className="container about-strip-inner">
          <div className="about-strip-logo">
            <BrandLogo alt="" variant="footer" />
          </div>
          <div>
            <h2>Une marque de confiance</h2>
            <p>
              Depuis Saint-Louis, <strong>{entreprise.raison_sociale}</strong> s&apos;impose comme partenaire privilégié
              des professionnels de santé. Notre identité reflète notre engagement : solidité,
              précision et proximité avec ceux qui soignent.
            </p>
          </div>
        </div>
      </section>

      <section className="section pillars">
        <div className="container">
          <div className="section-header">
            <span className="section-label">Notre offre</span>
            <h2>Une gamme complète pour la santé</h2>
            <p>Quatre piliers pour répondre à l&apos;ensemble de vos besoins médicaux.</p>
          </div>
          <div className="pillars-grid">
            {PILLARS.map((p) => (
              <article key={p.num} className="pillar-card">
                <span className="pillar-icon-wrap">
                  <Icon icon={PILLAR_ICON_MAP[p.title]} size={28} className="pillar-icon" />
                </span>
                <span className="pillar-num">{p.num}</span>
                <h3>{p.title}</h3>
                <p>{p.text}</p>
                <Link to="/catalogue" className="pillar-link">
                  Explorer
                  <Icon icon={ArrowRight} size={16} className="pillar-link-arrow" />
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="specialites" className="section specialites">
        <div className="container">
          <div className="section-header">
            <span className="section-label">Catalogue</span>
            <h2>Parcourir par spécialité</h2>
            <p>
              Ophtalmologie, gynécologie, cardiologie, bloc opératoire — trouvez les produits adaptés
              à votre discipline.
            </p>
          </div>
          <div className="specialites-grid">
            {SPECIALITE_ICONS.map((spec) => (
              <Link
                key={spec.name}
                to={`/catalogue?specialite=${encodeURIComponent(spec.name)}`}
                className="specialite-card"
              >
                <span className="specialite-icon">
                  <Icon icon={spec.icon} size={26} />
                </span>
                <span className="specialite-name">{spec.name}</span>
              </Link>
            ))}
          </div>
          <div className="specialites-cta">
            <Link to="/catalogue" className="btn btn-primary">
              Voir tout le catalogue
            </Link>
          </div>
        </div>
      </section>

      <section className="section cta-banner">
        <div className="container cta-banner-inner">
          <div className="cta-banner-logo">
            <BrandLogo alt="" variant="footer" />
          </div>
          <div className="cta-banner-text">
            <h2>Un partenaire à vos côtés</h2>
            <p>
              Devis, conseils techniques ou informations produit — notre équipe commerciale vous
              répond avec réactivité.
            </p>
          </div>
          <a href="#contact" className="btn btn-light btn-lg">
            Demander un devis
          </a>
        </div>
      </section>
    </>
  );
}
