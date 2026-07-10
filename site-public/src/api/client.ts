import type {
  Categorie,
  Entreprise,
  ProduitDetail,
  ProduitsPage,
  SpecialiteGroupe,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || '/api/public/v1';

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`Erreur API ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function getEntreprise() {
  return fetchJson<Entreprise>('/entreprise');
}

export function getCategories() {
  return fetchJson<Categorie[]>('/categories');
}

export function getSpecialites() {
  return fetchJson<SpecialiteGroupe[]>('/specialites');
}

export function getProduits(params: {
  page?: number;
  per_page?: number;
  categorie_id?: number;
  specialite?: string;
  q?: string;
}) {
  const search = new URLSearchParams();
  if (params.page) search.set('page', String(params.page));
  if (params.per_page) search.set('per_page', String(params.per_page));
  if (params.categorie_id) search.set('categorie_id', String(params.categorie_id));
  if (params.specialite) search.set('specialite', params.specialite);
  if (params.q) search.set('q', params.q);

  const qs = search.toString();
  return fetchJson<ProduitsPage>(`/produits${qs ? `?${qs}` : ''}`);
}

export function getProduit(id: number) {
  return fetchJson<ProduitDetail>(`/produits/${id}`);
}
