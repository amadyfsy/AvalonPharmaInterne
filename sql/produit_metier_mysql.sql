-- Fiches métier par catégorie (codes : medicaments | dispositifs | equipement)
-- À exécuter une fois sur les bases MySQL existantes.
--
-- Préférez le script idempotent (vérifie si les colonnes existent) :
--   cd <répertoire contenant config.py>
--   python GestAvalon/migrate_produit_metier_db.py

ALTER TABLE categories_produits
  ADD COLUMN code_formulaire VARCHAR(50) NULL;

CREATE INDEX ix_categories_produits_code_formulaire ON categories_produits (code_formulaire);

ALTER TABLE produits
  ADD COLUMN donnees_metier JSON NULL;

-- Stock par lot (source de vérité du stock produit)
ALTER TABLE lots
  ADD COLUMN quantite_disponible INT NOT NULL DEFAULT 0;

-- Initialiser le stock lot à partir des mouvements existants, sinon quantité initiale.
UPDATE lots l
LEFT JOIN (
  SELECT lot_id,
         SUM(
           CASE
             WHEN type_mouvement IN ('entree', 'retour') THEN quantite
             WHEN type_mouvement IN ('sortie', 'ajustement') THEN -quantite
             ELSE 0
           END
         ) AS qte
  FROM mouvements_stock
  WHERE lot_id IS NOT NULL
  GROUP BY lot_id
) m ON m.lot_id = l.id
SET l.quantite_disponible = GREATEST(0, COALESCE(m.qte, l.quantite_initiale, 0));

-- Exemple : lier des catégories existantes (adapter les noms ou utiliser des UPDATE par id)
-- UPDATE categories_produits SET code_formulaire = 'medicaments' WHERE nom LIKE '%Médicament%';
-- UPDATE categories_produits SET code_formulaire = 'dispositifs' WHERE nom LIKE '%Dispositif%';
-- UPDATE categories_produits SET code_formulaire = 'equipement' WHERE nom LIKE '%Équipement%' OR nom LIKE '%Biomédical%';
