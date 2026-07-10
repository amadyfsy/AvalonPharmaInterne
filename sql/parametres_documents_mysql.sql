-- Table des paramètres PDF (factures, BL, proformas). Exécuter une fois sur MySQL.
-- Ex. : mysql -u root -p medical_erp < GestAvalon/sql/parametres_documents_mysql.sql

CREATE TABLE IF NOT EXISTS parametres_documents (
    id INT NOT NULL PRIMARY KEY,
    raison_sociale VARCHAR(255) NOT NULL DEFAULT '',
    lieu_signature VARCHAR(120) NOT NULL DEFAULT 'St Louis',
    adresse_ligne VARCHAR(500) NOT NULL DEFAULT '',
    telephone VARCHAR(120) NOT NULL DEFAULT '',
    rc VARCHAR(120) NOT NULL DEFAULT '',
    ninea VARCHAR(120) NOT NULL DEFAULT '',
    email VARCHAR(255) NOT NULL DEFAULT '',
    compte_bancaire VARCHAR(255) NOT NULL DEFAULT '',
    logo_filename VARCHAR(255) NULL,
    pied_de_page TEXT NULL,
    devise_libelle VARCHAR(80) NOT NULL DEFAULT 'francs',
    updated_at DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO parametres_documents (id, raison_sociale, lieu_signature, devise_libelle)
VALUES (1, '', 'St Louis', 'francs');
