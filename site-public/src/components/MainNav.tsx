import { useEffect, useRef, useState, type FocusEvent } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { ChevronDown, Menu, X } from 'lucide-react';
import { getCategories } from '../api/client';
import { CATALOG_CATEGORY_DEFS } from '../config/catalogMenu';
import {
  FEATURED_SPECIALTIES,
  SPECIALTY_MENU_GROUPS,
  specialtyCatalogUrl,
} from '../config/specialtyMenu';
import Icon from './Icon';
import CatalogMegaMenu from './CatalogMegaMenu';
import SpecialtyMegaMenu from './SpecialtyMegaMenu';
import type { Categorie } from '../types';

type OpenMenu = 'catalog' | 'specialty' | null;

function catalogCategoryUrl(cat: Categorie | undefined, defNom: string): string {
  if (cat?.id) return `/catalogue?categorie_id=${cat.id}`;
  const match = CATALOG_CATEGORY_DEFS.find(
    (d) => d.nom.toLowerCase() === defNom.toLowerCase(),
  );
  if (match) return `/catalogue?q=${encodeURIComponent(match.searchHint)}`;
  return '/catalogue';
}

function matchCategory(categories: Categorie[], nom: string): Categorie | undefined {
  const n = nom.toLowerCase();
  return categories.find((c) => c.nom.toLowerCase().includes(n) || n.includes(c.nom.toLowerCase()));
}

function useDropdownMenu() {
  const [openMenu, setOpenMenu] = useState<OpenMenu>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const open = (menu: OpenMenu) => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    setOpenMenu(menu);
  };

  const scheduleClose = () => {
    closeTimer.current = setTimeout(() => setOpenMenu(null), 280);
  };

  const cancelClose = () => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
  };

  const toggle = (menu: OpenMenu) => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    setOpenMenu((current) => (current === menu ? null : menu));
  };

  const close = () => setOpenMenu(null);

  return { openMenu, open, scheduleClose, cancelClose, toggle, close };
}

export default function MainNav() {
  const location = useLocation();
  const [categories, setCategories] = useState<Categorie[]>([]);
  const { openMenu, open, scheduleClose, cancelClose, toggle, close } = useDropdownMenu();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mobileCatalogOpen, setMobileCatalogOpen] = useState(false);
  const [mobileSpecialtyOpen, setMobileSpecialtyOpen] = useState(false);
  const catalogRef = useRef<HTMLDivElement>(null);
  const specialtyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    close();
    setMobileOpen(false);
    setMobileCatalogOpen(false);
    setMobileSpecialtyOpen(false);
  }, [location.pathname, location.search]);

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileOpen]);

  useEffect(() => {
    const syncHeaderOffset = () => {
      const header = document.querySelector('.header');
      if (header) {
        document.documentElement.style.setProperty(
          '--site-header-offset',
          `${header.getBoundingClientRect().bottom}px`,
        );
      }
    };
    syncHeaderOffset();
    window.addEventListener('resize', syncHeaderOffset);
    window.addEventListener('scroll', syncHeaderOffset, { passive: true });
    return () => {
      window.removeEventListener('resize', syncHeaderOffset);
      window.removeEventListener('scroll', syncHeaderOffset);
    };
  }, []);

  const isCatalogActive =
    location.pathname.startsWith('/catalogue') && !location.search.includes('specialite=');
  const isSpecialtyActive =
    location.pathname.startsWith('/catalogue') && location.search.includes('specialite=');

  const dropdownHandlers = (menu: OpenMenu, ref: React.RefObject<HTMLDivElement | null>) => ({
    onMouseEnter: () => open(menu),
    onMouseLeave: scheduleClose,
    onFocus: () => open(menu),
    onBlur: (e: FocusEvent) => {
      if (!ref.current?.contains(e.relatedTarget as Node)) scheduleClose();
    },
  });

  return (
    <>
      {openMenu && (
        <div
          className="mega-menu-backdrop"
          aria-hidden="true"
          onClick={close}
        />
      )}

      <nav className="main-nav" aria-label="Navigation principale">
        <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          Accueil
        </NavLink>

        <div
          className={`nav-dropdown ${openMenu === 'catalog' ? 'is-open' : ''}`}
          ref={catalogRef}
          {...dropdownHandlers('catalog', catalogRef)}
        >
          <button
            type="button"
            className={`nav-link nav-dropdown-trigger ${isCatalogActive ? 'active' : ''}`}
            aria-expanded={openMenu === 'catalog'}
            aria-haspopup="true"
            onMouseEnter={() => open('catalog')}
            onClick={() => toggle('catalog')}
          >
            Catalogue
            <Icon icon={ChevronDown} size={16} className="nav-chevron" />
          </button>

          <div
            className="mega-menu-panel"
            onMouseEnter={cancelClose}
            onMouseLeave={scheduleClose}
          >
            <CatalogMegaMenu
              categories={categories}
              categoryUrl={catalogCategoryUrl}
              matchCategory={matchCategory}
            />
          </div>
        </div>

        <div
          className={`nav-dropdown ${openMenu === 'specialty' ? 'is-open' : ''}`}
          ref={specialtyRef}
          {...dropdownHandlers('specialty', specialtyRef)}
        >
          <button
            type="button"
            className={`nav-link nav-dropdown-trigger ${isSpecialtyActive ? 'active' : ''}`}
            aria-expanded={openMenu === 'specialty'}
            aria-haspopup="true"
            onMouseEnter={() => open('specialty')}
            onClick={() => toggle('specialty')}
          >
            Spécialités
            <Icon icon={ChevronDown} size={16} className="nav-chevron" />
          </button>
          <div
            className="mega-menu-panel"
            onMouseEnter={cancelClose}
            onMouseLeave={scheduleClose}
          >
            <SpecialtyMegaMenu />
          </div>
        </div>

        <a href="/#about" className="nav-link nav-anchor">
          À propos
        </a>
        <a href="/#contact" className="btn btn-primary btn-nav">
          Nous contacter
        </a>
      </nav>

      <button
        type="button"
        className="nav-mobile-toggle"
        aria-expanded={mobileOpen}
        aria-label={mobileOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
        onClick={() => setMobileOpen((v) => !v)}
      >
        <Icon icon={mobileOpen ? X : Menu} size={24} />
      </button>

      <div className={`mobile-nav ${mobileOpen ? 'is-open' : ''}`} aria-hidden={!mobileOpen}>
        <div className="mobile-nav-panel">
          <NavLink to="/" end className="mobile-nav-link" onClick={() => setMobileOpen(false)}>
            Accueil
          </NavLink>

          <div className="mobile-nav-section">
            <button
              type="button"
              className="mobile-nav-link mobile-nav-accordion"
              aria-expanded={mobileCatalogOpen}
              onClick={() => setMobileCatalogOpen((v) => !v)}
            >
              Catalogue
              <Icon icon={ChevronDown} size={18} className={mobileCatalogOpen ? 'rotated' : ''} />
            </button>
            {mobileCatalogOpen && (
              <div className="mobile-submenu">
                <p className="mobile-submenu-label">Types de produits</p>
                <div className="mobile-specialty-grid">
                  {CATALOG_CATEGORY_DEFS.map((def) => {
                    const apiCat = matchCategory(categories, def.nom);
                    return (
                      <Link
                        key={def.nom}
                        to={catalogCategoryUrl(apiCat, def.nom)}
                        className="mobile-specialty-tile"
                        onClick={() => setMobileOpen(false)}
                      >
                        <Icon icon={def.icon} size={20} />
                        <span>{def.nom}</span>
                      </Link>
                    );
                  })}
                </div>
                <Link
                  to="/catalogue"
                  className="btn btn-primary btn-sm mobile-submenu-cta"
                  onClick={() => setMobileOpen(false)}
                >
                  Tout le catalogue
                </Link>
              </div>
            )}
          </div>

          <div className="mobile-nav-section">
            <button
              type="button"
              className="mobile-nav-link mobile-nav-accordion"
              aria-expanded={mobileSpecialtyOpen}
              onClick={() => setMobileSpecialtyOpen((v) => !v)}
            >
              Spécialités
              <Icon icon={ChevronDown} size={18} className={mobileSpecialtyOpen ? 'rotated' : ''} />
            </button>
            {mobileSpecialtyOpen && (
              <div className="mobile-submenu mobile-submenu-specialties">
                <p className="mobile-submenu-label">Populaires</p>
                <div className="mobile-specialty-grid">
                  {FEATURED_SPECIALTIES.map((spec) => (
                    <Link
                      key={spec.name}
                      to={specialtyCatalogUrl(spec.name)}
                      className="mobile-specialty-tile"
                      onClick={() => setMobileOpen(false)}
                    >
                      <Icon icon={spec.icon} size={20} />
                      <span>{spec.name}</span>
                    </Link>
                  ))}
                </div>
                {SPECIALTY_MENU_GROUPS.map((group) => (
                  <div key={group.title}>
                    <p className="mobile-submenu-label">{group.title}</p>
                    <div className="mobile-specialty-grid">
                      {group.items.map((spec) => (
                        <Link
                          key={`${group.title}-${spec.name}`}
                          to={specialtyCatalogUrl(spec.name)}
                          className="mobile-specialty-tile"
                          onClick={() => setMobileOpen(false)}
                        >
                          <Icon icon={spec.icon} size={18} />
                          <span>{spec.name}</span>
                        </Link>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <a href="/#about" className="mobile-nav-link" onClick={() => setMobileOpen(false)}>
            À propos
          </a>
          <a href="/#contact" className="btn btn-primary mobile-nav-cta" onClick={() => setMobileOpen(false)}>
            Nous contacter
          </a>
        </div>
      </div>
    </>
  );
}
