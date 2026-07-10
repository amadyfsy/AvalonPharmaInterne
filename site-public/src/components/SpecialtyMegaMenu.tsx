import { Link } from 'react-router-dom';
import { ArrowRight, Sparkles } from 'lucide-react';
import {
  FEATURED_SPECIALTIES,
  SPECIALTY_MENU_GROUPS,
  specialtyCatalogUrl,
} from '../config/specialtyMenu';
import Icon from './Icon';

export default function SpecialtyMegaMenu() {
  return (
    <div className="mega-menu mega-menu--specialties" role="menu" aria-label="Sous-menu spécialités">
      <div className="specialty-mega">
        <aside className="specialty-mega-intro">
          <span className="specialty-mega-badge">
            <Icon icon={Sparkles} size={16} />
            15+ domaines
          </span>
          <h3>Nos spécialités médicales</h3>
          <p>
            Parcourez notre catalogue par discipline : de l&apos;ophtalmologie à la gynécologie, du
            bloc opératoire au laboratoire.
          </p>
          <div className="specialty-mega-featured">
            <span className="specialty-mega-featured-label">Les plus demandées</span>
            <div className="specialty-mega-featured-grid">
              {FEATURED_SPECIALTIES.map((spec) => (
                <Link
                  key={spec.name}
                  to={specialtyCatalogUrl(spec.name)}
                  className="specialty-featured-tile"
                  role="menuitem"
                >
                  <Icon icon={spec.icon} size={20} />
                  <span>{spec.name}</span>
                </Link>
              ))}
            </div>
          </div>
          <Link to="/catalogue" className="specialty-mega-all-link" role="menuitem">
            Voir tout le catalogue
            <Icon icon={ArrowRight} size={16} />
          </Link>
        </aside>

        <div className="specialty-mega-groups">
          {SPECIALTY_MENU_GROUPS.map((group) => (
            <section key={group.title} className="specialty-mega-group">
              <header className="specialty-mega-group-head">
                <span className="specialty-mega-group-icon">
                  <Icon icon={group.icon} size={20} />
                </span>
                <div>
                  <h4>{group.title}</h4>
                  <p>{group.subtitle}</p>
                </div>
              </header>
              <ul className="specialty-mega-tiles">
                {group.items.map((spec) => (
                  <li key={`${group.title}-${spec.name}`}>
                    <Link
                      to={specialtyCatalogUrl(spec.name)}
                      className="specialty-mega-tile"
                      role="menuitem"
                    >
                      <span className="specialty-mega-tile-icon">
                        <Icon icon={spec.icon} size={22} />
                      </span>
                      <span className="specialty-mega-tile-label">{spec.name}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
