-- Lots : dates et fournisseur facultatifs (création produit sans lot complet).
-- À exécuter une fois sur les bases MySQL existantes.

ALTER TABLE lots MODIFY COLUMN date_fabrication DATE NULL;
ALTER TABLE lots MODIFY COLUMN date_peremption DATE NULL;
ALTER TABLE lots MODIFY COLUMN fournisseur_id INT NULL;
