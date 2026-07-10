import { Link } from 'react-router-dom';
import type { ProduitResume } from '../types';

interface ProductCardProps {
  produit: ProduitResume;
}

function formatPrice(value: number) {
  return new Intl.NumberFormat('fr-FR', {
    style: 'decimal',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export default function ProductCard({ produit }: ProductCardProps) {
  const img = produit.photos.photo_principale_url;

  return (
    <Link to={`/catalogue/${produit.id}`} className="product-card">
      <div className="product-card-image">
        {img ? (
          <img src={img} alt={produit.designation} loading="lazy" />
        ) : (
          <div className="product-card-placeholder" aria-hidden="true">
            <span>Avalon</span>
          </div>
        )}
        {produit.specialite && <span className="product-badge">{produit.specialite}</span>}
      </div>
      <div className="product-card-body">
        <span className="product-ref">{produit.reference}</span>
        <h3>{produit.designation}</h3>
        {produit.description && <p className="product-desc">{produit.description}</p>}
        <div className="product-card-footer">
          <span className="product-cat">{produit.categorie}</span>
          <span className="product-price">{formatPrice(produit.prix_vente_ttc)} FCFA</span>
        </div>
      </div>
    </Link>
  );
}
