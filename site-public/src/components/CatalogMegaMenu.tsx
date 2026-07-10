import { Link } from 'react-router-dom';
import { ArrowRight, LayoutGrid, Search } from 'lucide-react';
import { CATALOG_CATEGORY_DEFS } from '../config/catalogMenu';
import { FEATURED_SPECIALTIES, specialtyCatalogUrl } from '../config/specialtyMenu';
import Icon from './Icon';
import SenegalFlag from './SenegalFlag';
import type { Categorie } from '../types';

interface CatalogMegaMenuProps {
  categories: Categorie[];
  categoryUrl: (cat: Categorie | undefined, defNom: string) => string;
  matchCategory: (categories: Categorie[], nom: string) => Categorie | undefined;
}

export default function CatalogMegaMenu({
  categories,
  categoryUrl,
  matchCategory,
}: CatalogMegaMenuProps) {
  return (
    <div className="mega-menu mega-menu--catalog" role="menu" aria-label="Sous-menu catalogue">
      <div className="catalog-mega">
        <aside className="catalog-mega-intro">
          <span className="catalog-mega-badge">
            <Icon icon={LayoutGrid} size={16} />
            4 univers produits
          </span>
          <h3>Notre catalogue</h3>
          <p>
            Médicaments, consommables, implants et équipements biomédicaux — une offre complète
            pour les établissements de santé au Sénégal.
          </p>
          <div className="catalog-mega-stats">
            <div className="catalog-mega-stat">
              <strong>500+</strong>
              <span>Références</span>
            </div>
            <div className="catalog-mega-stat">
              <strong>4</strong>
              <span>Familles</span>
            </div>
            <div className="catalog-mega-stat catalog-mega-stat-flag">
              <SenegalFlag className="catalog-mega-flag" />
              <span>National</span>
            </div>
          </div>
          <Link to="/catalogue" className="btn btn-light btn-sm catalog-mega-cta" role="menuitem">
            <Icon icon={Search} size={16} />
            Explorer tout le catalogue
          </Link>
        </aside>

        <div className="catalog-mega-body">
          <header className="catalog-mega-head">
            <h4>Parcourir par type de produit</h4>
            <p>Sélectionnez une famille pour accéder aux références correspondantes.</p>
          </header>

          <div className="catalog-mega-grid">
            {CATALOG_CATEGORY_DEFS.map((def) => {
              const apiCat = matchCategory(categories, def.nom);
              return (
                <Link
                  key={def.nom}
                  to={categoryUrl(apiCat, def.nom)}
                  className="catalog-mega-card"
                  role="menuitem"
                >
                  <span className="catalog-mega-card-icon">
                    <Icon icon={def.icon} size={28} />
                  </span>
                  <div className="catalog-mega-card-content">
                    <strong>{def.nom}</strong>
                    <span className="catalog-mega-card-desc">{def.longDescription}</span>
                    <ul className="catalog-mega-tags">
                      {def.examples.map((tag) => (
                        <li key={tag}>{tag}</li>
                      ))}
                    </ul>
                  </div>
                  <Icon icon={ArrowRight} size={18} className="catalog-mega-card-arrow" />
                </Link>
              );
            })}
          </div>

          <footer className="catalog-mega-footer">
            <span className="catalog-mega-footer-label">Accès rapide par spécialité</span>
            <div className="catalog-mega-footer-links">
              {FEATURED_SPECIALTIES.map((spec) => (
                <Link
                  key={spec.name}
                  to={specialtyCatalogUrl(spec.name)}
                  className="catalog-mega-footer-chip"
                  role="menuitem"
                >
                  <Icon icon={spec.icon} size={16} />
                  {spec.name}
                </Link>
              ))}
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}
