export interface Entreprise {
  raison_sociale: string;
  slogan: string;
  site_web: string;
  adresse: string;
  telephone: string;
  email: string;
  rc: string;
  ninea: string;
  pied_de_page: string | null;
}

export interface Categorie {
  id: number;
  nom: string;
  description: string | null;
  code_formulaire: string;
}

export interface SpecialiteGroupe {
  groupe: string;
  specialites: string[];
}

export interface PhotoGalerie {
  id: number;
  fichier: string;
  url: string | null;
  ordre: number;
  legende: string | null;
}

export interface PhotosProduit {
  photo_principale: string | null;
  photo_principale_url: string | null;
  galerie: PhotoGalerie[];
}

export interface ProduitResume {
  id: number;
  reference: string;
  designation: string;
  description: string | null;
  categorie_id: number;
  categorie: string | null;
  code_formulaire: string | null;
  specialite: string | null;
  forme: string;
  unite: string;
  prix_vente_ht: number;
  prix_vente_ttc: number;
  tva: number;
  photos: PhotosProduit;
}

export interface ProduitDetail extends ProduitResume {
  donnees_metier: Record<string, string>;
}

export interface ProduitsPage {
  items: ProduitResume[];
  page: number;
  per_page: number;
  total: number;
  pages: number;
}
