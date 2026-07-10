import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Mail, MapPin, Phone } from 'lucide-react';
import BrandLogo from './BrandLogo';
import Icon from './Icon';
import MainNav from './MainNav';
import { BRAND_LOCATION } from '../config/brand';
import type { Entreprise } from '../types';

interface LayoutProps {
  entreprise: Entreprise;
  children: ReactNode;
}

export default function Layout({ entreprise, children }: LayoutProps) {
  return (
    <div className="site">
      <div className="topbar">
        <div className="container topbar-inner">
          <span className="topbar-item">
            <Icon icon={MapPin} size={14} className="icon-mint" />
            {BRAND_LOCATION}
          </span>
          {entreprise.telephone && (
            <a href={`tel:${entreprise.telephone.replace(/\s/g, '')}`} className="topbar-item">
              <Icon icon={Phone} size={14} className="icon-mint" />
              {entreprise.telephone}
            </a>
          )}
          {entreprise.email && (
            <a href={`mailto:${entreprise.email}`} className="topbar-item">
              <Icon icon={Mail} size={14} className="icon-mint" />
              {entreprise.email}
            </a>
          )}
        </div>
      </div>

      <header className="header">
        <div className="container header-inner">
          <Link to="/" className="brand brand--horizontal">
            <BrandLogo alt={entreprise.raison_sociale} variant="header" />
            <span className="brand-slogan-only">{entreprise.slogan}</span>
          </Link>
          <MainNav />
        </div>
      </header>

      <main>{children}</main>

      <footer id="contact" className="footer">
        <div className="footer-wave" aria-hidden="true" />
        <div className="container footer-main">
          <div className="footer-brand">
            <BrandLogo alt={entreprise.raison_sociale} variant="footer" />
            <h3>{entreprise.raison_sociale}</h3>
            <p className="footer-slogan">{entreprise.slogan}</p>
            <p className="footer-about">
              Distributeur de référence en produits pharmaceutiques, dispositifs médicaux et équipements
              biomédicaux pour les professionnels de santé au Sénégal.
            </p>
          </div>

          <div className="footer-col">
            <h4>Navigation</h4>
            <ul>
              <li><Link to="/">Accueil</Link></li>
              <li><Link to="/catalogue">Catalogue produits</Link></li>
              <li><a href="/#specialites">Spécialités</a></li>
              <li><a href="/#about">À propos</a></li>
            </ul>
          </div>

          <div className="footer-col">
            <h4>Contact</h4>
            <ul>
              {entreprise.adresse && <li>{entreprise.adresse}</li>}
              {entreprise.telephone && (
                <li>
                  <a href={`tel:${entreprise.telephone.replace(/\s/g, '')}`}>{entreprise.telephone}</a>
                </li>
              )}
              {entreprise.email && (
                <li>
                  <a href={`mailto:${entreprise.email}`}>{entreprise.email}</a>
                </li>
              )}
              {entreprise.site_web && (
                <li>
                  <a href={entreprise.site_web} target="_blank" rel="noopener noreferrer">
                    {entreprise.site_web.replace(/^https?:\/\//, '')}
                  </a>
                </li>
              )}
            </ul>
          </div>

          <div className="footer-col">
            <h4>Informations légales</h4>
            <ul>
              {entreprise.rc && <li>RC : {entreprise.rc}</li>}
              {entreprise.ninea && <li>NINEA : {entreprise.ninea}</li>}
              {entreprise.pied_de_page && <li>{entreprise.pied_de_page}</li>}
            </ul>
          </div>
        </div>

        <div className="footer-bottom">
          <div className="container footer-bottom-inner">
            <p>&copy; {new Date().getFullYear()} {entreprise.raison_sociale}. Tous droits réservés.</p>
            <p className="footer-motto">Serving those who care for others</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
