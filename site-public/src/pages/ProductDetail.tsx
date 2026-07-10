import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getProduit } from '../api/client';
import type { ProduitDetail } from '../types';

const METIER_LABELS: Record<string, string> = {
  specialite: 'Spécialité',
  nom_commercial_dci: 'Nom commercial / DCI',
  indication_therapeutique: 'Indication thérapeutique',
  code_ucd_cip: 'Code UCD / CIP',
  mode_administration: 'Mode d’administration',
  type_dispositif: 'Type de dispositif',
  reference_sku: 'Référence SKU',
  taille_caracteristique: 'Taille / caractéristique',
  conditionnement: 'Conditionnement',
  fonction_principale: 'Fonction principale',
  garantie_maintenance: 'Garantie & maintenance',
  formation_requise: 'Formation requise',
};

function formatPrice(value: number) {
  return new Intl.NumberFormat('fr-FR', {
    style: 'decimal',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  const [produit, setProduit] = useState<ProduitDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeImage, setActiveImage] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getProduit(Number(id))
      .then((p) => {
        setProduit(p);
        setActiveImage(p.photos.photo_principale_url);
      })
      .catch(() => setError('Produit introuvable.'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="container product-detail-loading">
        <p>Chargement du produit…</p>
      </div>
    );
  }

  if (error || !produit) {
    return (
      <div className="container product-detail-error">
        <p>{error || 'Produit introuvable.'}</p>
        <Link to="/catalogue" className="btn btn-primary">
          Retour au catalogue
        </Link>
      </div>
    );
  }

  const metierEntries = Object.entries(produit.donnees_metier || {}).filter(
    ([, v]) => v && String(v).trim(),
  );

  const allImages = [
    produit.photos.photo_principale_url,
    ...produit.photos.galerie.map((g) => g.url),
  ].filter(Boolean) as string[];

  return (
    <div className="product-detail-page">
      <div className="container">
        <nav className="breadcrumb">
          <Link to="/catalogue">Catalogue</Link>
          <span>/</span>
          <span>{produit.designation}</span>
        </nav>

        <div className="product-detail-grid">
          <div className="product-gallery">
            <div className="product-gallery-main">
              {activeImage ? (
                <img src={activeImage} alt={produit.designation} />
              ) : (
                <div className="product-gallery-placeholder" aria-hidden="true">
                  <span>Avalon</span>
                </div>
              )}
            </div>
            {allImages.length > 1 && (
              <div className="product-gallery-thumbs">
                {allImages.map((url) => (
                  <button
                    key={url}
                    type="button"
                    className={activeImage === url ? 'thumb active' : 'thumb'}
                    onClick={() => setActiveImage(url)}
                  >
                    <img src={url} alt="" />
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="product-info">
            <span className="product-ref">{produit.reference}</span>
            <h1>{produit.designation}</h1>
            <div className="product-tags">
              {produit.categorie && <span className="tag">{produit.categorie}</span>}
              {produit.specialite && <span className="tag tag-accent">{produit.specialite}</span>}
            </div>

            <div className="product-price-block">
              <span className="product-price-label">Prix TTC</span>
              <span className="product-price-value">{formatPrice(produit.prix_vente_ttc)} FCFA</span>
              <span className="product-price-ht">
                HT : {formatPrice(produit.prix_vente_ht)} FCFA (TVA {produit.tva}%)
              </span>
            </div>

            {produit.description && (
              <div className="product-description">
                <h2>Description</h2>
                <p>{produit.description}</p>
              </div>
            )}

            {metierEntries.length > 0 && (
              <div className="product-specs">
                <h2>Caractéristiques</h2>
                <dl>
                  {metierEntries.map(([key, value]) => (
                    <div key={key} className="spec-row">
                      <dt>{METIER_LABELS[key] || key}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}

            <a href="#contact" className="btn btn-primary">
              Demander un devis
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
