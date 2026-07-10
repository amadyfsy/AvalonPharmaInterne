import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { RotateCcw, Search } from 'lucide-react';
import { getCategories, getProduits, getSpecialites } from '../api/client';
import Icon from '../components/Icon';
import ProductCard from '../components/ProductCard';
import type { Categorie, ProduitResume, SpecialiteGroupe } from '../types';

export default function Catalog() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [categories, setCategories] = useState<Categorie[]>([]);
  const [specialites, setSpecialites] = useState<SpecialiteGroupe[]>([]);
  const [produits, setProduits] = useState<ProduitResume[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const page = Number(searchParams.get('page') || '1');
  const categorieId = Number(searchParams.get('categorie_id') || '0');
  const specialite = searchParams.get('specialite') || '';
  const q = searchParams.get('q') || '';

  const updateParams = useCallback(
    (updates: Record<string, string>) => {
      const next = new URLSearchParams(searchParams);
      Object.entries(updates).forEach(([k, v]) => {
        if (!v || v === '0') next.delete(k);
        else next.set(k, v);
      });
      if (!('page' in updates)) next.delete('page');
      setSearchParams(next);
    },
    [searchParams, setSearchParams],
  );

  useEffect(() => {
    Promise.all([getCategories(), getSpecialites()])
      .then(([cats, specs]) => {
        setCategories(cats);
        setSpecialites(specs);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    setError('');
    getProduits({
      page,
      per_page: 24,
      categorie_id: categorieId || undefined,
      specialite: specialite || undefined,
      q: q || undefined,
    })
      .then((data) => {
        setProduits(data.items);
        setTotal(data.total);
        setPages(data.pages);
      })
      .catch(() => setError('Impossible de charger le catalogue.'))
      .finally(() => setLoading(false));
  }, [page, categorieId, specialite, q]);

  const allSpecialites = specialites.flatMap((g) => g.specialites);

  return (
    <div className="catalog-page">
      <div className="catalog-hero">
        <div className="container">
          <h1>Catalogue produits</h1>
          <p>
            Médicaments, dispositifs médicaux et équipements biomédicaux — filtrez par catégorie
            ou spécialité (Ophtalmologie, Gynécologie, etc.).
          </p>
        </div>
      </div>

      <div className="container catalog-layout">
        <aside className="catalog-filters">
          <div className="filter-block">
            <h3>Recherche</h3>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const fd = new FormData(e.currentTarget);
                updateParams({ q: String(fd.get('q') || '') });
              }}
            >
              <input
                type="search"
                name="q"
                defaultValue={q}
                placeholder="Nom, référence…"
                className="filter-input"
              />
              <button type="submit" className="btn btn-primary btn-sm btn-icon">
                <Icon icon={Search} size={16} />
                Rechercher
              </button>
            </form>
          </div>

          <div className="filter-block">
            <h3>Catégorie</h3>
            <div className="filter-chips">
              <button
                type="button"
                className={!categorieId ? 'filter-chip active' : 'filter-chip'}
                onClick={() => updateParams({ categorie_id: '' })}
              >
                Toutes
              </button>
              {categories.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  className={categorieId === c.id ? 'filter-chip active' : 'filter-chip'}
                  onClick={() => updateParams({ categorie_id: String(c.id) })}
                >
                  {c.nom}
                </button>
              ))}
            </div>
          </div>

          <div className="filter-block">
            <h3>Spécialité</h3>
            <select
              className="filter-select"
              value={specialite}
              onChange={(e) => updateParams({ specialite: e.target.value })}
            >
              <option value="">Toutes les spécialités</option>
              {specialites.map((g) => (
                <optgroup key={g.groupe} label={g.groupe}>
                  {g.specialites.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
            <div className="filter-chips filter-chips-wrap">
              {allSpecialites.slice(0, 8).map((s) => (
                <button
                  key={s}
                  type="button"
                  className={specialite === s ? 'filter-chip active' : 'filter-chip'}
                  onClick={() => updateParams({ specialite: specialite === s ? '' : s })}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {(categorieId || specialite || q) && (
            <button
              type="button"
              className="btn btn-outline btn-sm filter-reset btn-icon"
              onClick={() => setSearchParams({})}
            >
              <Icon icon={RotateCcw} size={16} />
              Réinitialiser les filtres
            </button>
          )}
        </aside>

        <section className="catalog-results">
          <div className="catalog-meta">
            <span>
              {loading ? 'Chargement…' : `${total} produit${total !== 1 ? 's' : ''}`}
            </span>
            {(specialite || q) && (
              <span className="catalog-active-filters">
                {specialite && <span className="tag">{specialite}</span>}
                {q && <span className="tag">« {q} »</span>}
              </span>
            )}
          </div>

          {error && <p className="catalog-error">{error}</p>}

          {!loading && !error && produits.length === 0 && (
            <div className="catalog-empty">
              <p>Aucun produit ne correspond à vos critères.</p>
              <button type="button" className="btn btn-outline" onClick={() => setSearchParams({})}>
                Voir tout le catalogue
              </button>
            </div>
          )}

          <div className="products-grid">
            {produits.map((p) => (
              <ProductCard key={p.id} produit={p} />
            ))}
          </div>

          {pages > 1 && (
            <div className="pagination">
              <button
                type="button"
                className="btn btn-outline btn-sm"
                disabled={page <= 1}
                onClick={() => updateParams({ page: String(page - 1) })}
              >
                Précédent
              </button>
              <span>
                Page {page} / {pages}
              </span>
              <button
                type="button"
                className="btn btn-outline btn-sm"
                disabled={page >= pages}
                onClick={() => updateParams({ page: String(page + 1) })}
              >
                Suivant
              </button>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
