-- SQL enrichi et lié depuis factures_extraites.sql + tentative Google Sheet MarcheTambaProduits
-- Format: SQLite. Inclut tables normalisées, alias, historique des prix et vues de contrôle.
PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE catalog_sources (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT,
  status TEXT NOT NULL,
  note TEXT,
  checked_at TEXT DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO "catalog_sources" VALUES(1,'MarcheTambaProduits Google Sheet','https://docs.google.com/spreadsheets/d/1rN8i4UZruzK4erFb8aRH4yWSqgFwUeDAf7bkQF8MlV4/edit?usp=sharing','partial_access_only','Le lien affiche le classeur et les onglets, mais seules les entêtes visibles ont été récupérables ici: Prduits, Quantite, P.Unitaire, Total. Aucune ligne produit exploitable n’a été disponible sans export CSV/XLSX ou connexion Drive.','2026-05-10 13:16:43');
CREATE TABLE client_aliases (
  id INTEGER PRIMARY KEY,
  client_id INTEGER NOT NULL,
  alias TEXT NOT NULL,
  normalized_alias TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'factures_zip',
  UNIQUE(client_id, normalized_alias),
  FOREIGN KEY (client_id) REFERENCES clients(id)
);
INSERT INTO "client_aliases" VALUES(1,1,'HÔPITAL TIVAOUANE','hopital tivaouane','factures_zip');
INSERT INTO "client_aliases" VALUES(2,2,'Dr Abdoul Ly','dr abdoul ly','factures_zip');
INSERT INTO "client_aliases" VALUES(3,3,'Dr Ousseynou Faye','dr ousseynou faye','factures_zip');
INSERT INTO "client_aliases" VALUES(4,4,'Centre Hospitalier Régional de Ndioum','centre hospitalier regional de ndioum','factures_zip');
INSERT INTO "client_aliases" VALUES(5,5,'CHR de Saint-Louis','chr de saint louis','factures_zip');
INSERT INTO "client_aliases" VALUES(6,6,'Lk GROUP SARL','lk group sarl','factures_zip');
INSERT INTO "client_aliases" VALUES(7,7,'Mme Sow','mme sow','factures_zip');
INSERT INTO "client_aliases" VALUES(8,8,'CHR de Ndioum','chr de ndioum','factures_zip');
INSERT INTO "client_aliases" VALUES(9,9,'RAJUNT DISTRIBUTION','rajunt distribution','factures_zip');
INSERT INTO "client_aliases" VALUES(10,10,'Inspection Médicale scolaire de St-Louis','inspection medicale scolaire de st louis','factures_zip');
INSERT INTO "client_aliases" VALUES(11,11,'Centre de sante Serigne Saliou Touba','centre de sante serigne saliou touba','factures_zip');
INSERT INTO "client_aliases" VALUES(12,12,'AM2S','am2s','factures_zip');
INSERT INTO "client_aliases" VALUES(13,13,'Medical distribution','medical distribution','factures_zip');
INSERT INTO "client_aliases" VALUES(14,14,'Centre Hospitalier Maguette Lo de Linguere','centre hospitalier maguette lo de linguere','factures_zip');
INSERT INTO "client_aliases" VALUES(15,15,'Centre de santé Keur Niang','centre de sante keur niang','factures_zip');
INSERT INTO "client_aliases" VALUES(16,16,'CHR Saint-Louis','chr saint louis','factures_zip');
INSERT INTO "client_aliases" VALUES(17,17,'Pharmacie MIFTAH SERIGNE Alioune Gueye','pharmacie miftah serigne alioune gueye','factures_zip');
INSERT INTO "client_aliases" VALUES(18,18,'Centre de santé 28 de Touba','centre de sante 28 de touba','factures_zip');
INSERT INTO "client_aliases" VALUES(19,19,'EDA','eda','factures_zip');
INSERT INTO "client_aliases" VALUES(20,20,'HÔPITAL OUROSSOGUI','hopital ourossogui','factures_zip');
INSERT INTO "client_aliases" VALUES(21,21,'CHN MATLABOUL FAWZAINI de TOUBA','chn matlaboul fawzaini de touba','factures_zip');
INSERT INTO "client_aliases" VALUES(22,22,'Mme Marie Diouf','mme marie diouf','factures_zip');
INSERT INTO "client_aliases" VALUES(23,23,'Centre de santé de Bambey','centre de sante de bambey','factures_zip');
INSERT INTO "client_aliases" VALUES(24,24,'Centre de santé Guemoul','centre de sante guemoul','factures_zip');
INSERT INTO "client_aliases" VALUES(25,25,'Centre de Santé Ndam Touba','centre de sante ndam touba','factures_zip');
CREATE TABLE clients (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);
INSERT INTO "clients" VALUES(1,'HÔPITAL TIVAOUANE');
INSERT INTO "clients" VALUES(2,'Dr Abdoul Ly');
INSERT INTO "clients" VALUES(3,'Dr Ousseynou Faye');
INSERT INTO "clients" VALUES(4,'Centre Hospitalier Régional de Ndioum');
INSERT INTO "clients" VALUES(5,'CHR de Saint-Louis');
INSERT INTO "clients" VALUES(6,'Lk GROUP SARL');
INSERT INTO "clients" VALUES(7,'Mme Sow');
INSERT INTO "clients" VALUES(8,'CHR de Ndioum');
INSERT INTO "clients" VALUES(9,'RAJUNT DISTRIBUTION');
INSERT INTO "clients" VALUES(10,'Inspection Médicale scolaire de St-Louis');
INSERT INTO "clients" VALUES(11,'Centre de sante Serigne Saliou Touba');
INSERT INTO "clients" VALUES(12,'AM2S');
INSERT INTO "clients" VALUES(13,'Medical distribution');
INSERT INTO "clients" VALUES(14,'Centre Hospitalier Maguette Lo de Linguere');
INSERT INTO "clients" VALUES(15,'Centre de santé Keur Niang');
INSERT INTO "clients" VALUES(16,'CHR Saint-Louis');
INSERT INTO "clients" VALUES(17,'Pharmacie MIFTAH SERIGNE Alioune Gueye');
INSERT INTO "clients" VALUES(18,'Centre de santé 28 de Touba');
INSERT INTO "clients" VALUES(19,'EDA');
INSERT INTO "clients" VALUES(20,'HÔPITAL OUROSSOGUI');
INSERT INTO "clients" VALUES(21,'CHN MATLABOUL FAWZAINI de TOUBA');
INSERT INTO "clients" VALUES(22,'Mme Marie Diouf');
INSERT INTO "clients" VALUES(23,'Centre de santé de Bambey');
INSERT INTO "clients" VALUES(24,'Centre de santé Guemoul');
INSERT INTO "clients" VALUES(25,'Centre de Santé Ndam Touba');
CREATE TABLE invoice_documents (
  id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL UNIQUE,
  source_file TEXT NOT NULL,
  original_document_type TEXT,
  extracted_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (order_id) REFERENCES orders(id)
);
INSERT INTO "invoice_documents" VALUES(1,1,'FACTURE  N◦2025_11_03.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(2,2,'FACTURE No 2025_08_08.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(3,3,'FACTURE No 2025_08_09.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(4,4,'FACTURE No 2025_09_05.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(5,5,'FACTURE No 2025_11_02.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(6,6,'FACTURE No 2025_11_03.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(7,7,'FACTURE No 2025_11_05.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(8,8,'FACTURE No 2025_11_06.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(9,9,'FACTURE No 2025_12_01.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(10,10,'FACTURE No 2025_12_02.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(11,11,'FACTURE No 2025_12_04.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(12,12,'FACTURE No 2026_01_01.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(13,13,'FACTURE No 2026_01_02.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(14,14,'FACTURE No 2026_01_03.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(15,15,'FACTURE No 2026_01_04.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(16,16,'FACTURE No 2026_01_05.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(17,17,'FACTURE No 2026_02_01.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(18,18,'FACTURE No 2026_02_03.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(19,19,'FACTURE No 2026_03_01.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(20,20,'FACTURE No 2026_03_02.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(21,21,'FACTURE No 2026_03_03.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(22,22,'FACTURE No 2026_03_04.docx','facture','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(23,23,'FACTURE No 2026_05_01.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(24,24,'FACTURE No 2026_05_02.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(25,25,'FACTURE No 2026_05_03.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(26,26,'FACTURE No 2026_05_04.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(27,27,'FACTURE N◦26_03_05.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(28,28,'FACTURE N◦26_04_01.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(29,29,'FACTURE N◦26_04_02.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(30,30,'FACTURE N◦26_04_03.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(31,31,'FACTURE N◦26_04_04.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(32,32,'FACTURE N◦26_04_05.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(33,33,'FACTURE N◦26_04_06.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(34,34,'FACTURE N◦26_04_08.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(35,35,'FACTURE N◦26_04_09.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(36,36,'FACTURE N◦26_04_10.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(37,37,'FACTURE N◦26_05_04.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(38,38,'PROFORMAT  EDA.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(39,39,'PROFORMAT  NDIOUM.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(40,40,'PROFORMAT  OUROSSOGUI.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(41,41,'PROFORMAT  Touba.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(42,42,'PROFORMAT  chr Saint_Louis_.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(43,43,'PROFORMAT.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(44,44,'PROFORMAT_.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(45,45,'PROFORMAT_2.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(46,46,'PROFORMAT_3.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(47,47,'PROFORMAT_Bambey.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(48,48,'PROFORMAT_CS_TOUBA.docx','proforma','2026-05-10 13:16:43');
INSERT INTO "invoice_documents" VALUES(49,49,'PROFORMAT_Touba.docx','proforma','2026-05-10 13:16:43');
CREATE TABLE order_items (
  id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  line_number INTEGER NOT NULL,
  quantity NUMERIC,
  unit_price NUMERIC,
  line_total NUMERIC,
  lot_number TEXT,
  production_date_text TEXT,
  expiry_date_text TEXT,
  product_name_raw TEXT,
  FOREIGN KEY (order_id) REFERENCES orders(id),
  FOREIGN KEY (product_id) REFERENCES products(id)
);
INSERT INTO "order_items" VALUES(1,1,1,1,2000,150,300000,NULL,NULL,NULL,'Gants Stériles T 7,5');
INSERT INTO "order_items" VALUES(2,1,2,2,250,3500,875000,NULL,NULL,NULL,'Drap d''accouchement avec poche de recueil post partum');
INSERT INTO "order_items" VALUES(3,2,3,1,1,520000,520000,NULL,NULL,NULL,'Réfrigérateur médical 400L');
INSERT INTO "order_items" VALUES(4,3,4,1,1,420000,420000,NULL,NULL,NULL,'Réfrigérateur médical 150L');
INSERT INTO "order_items" VALUES(5,4,5,1,5,36000,180000,NULL,NULL,NULL,'Bandelettes Fluorescéine 8/50');
INSERT INTO "order_items" VALUES(6,5,1,1,2000,150,300000,'050525','05/2025','04/2030','Gants Stériles T 7,5');
INSERT INTO "order_items" VALUES(7,6,1,1,300,6500,1950000,'050525','05/2025','04/2030','Gants Stériles T 7,5');
INSERT INTO "order_items" VALUES(8,6,6,2,150,6500,975000,'050525','05/2025','04/2030','Gants Stériles T 8');
INSERT INTO "order_items" VALUES(9,6,7,3,10,32500,325000,'011325','01/2025','12/2029','Gants pour invasion utérine');
INSERT INTO "order_items" VALUES(10,6,8,4,1200,9860,11832000,'4541','01/2025','12/2028','Trousse Universelle');
INSERT INTO "order_items" VALUES(11,6,9,5,25,13985,349625,'k250609A01A','06/2025','06/2027','Surgicel');
INSERT INTO "order_items" VALUES(12,6,10,6,25,10985,274625,'20250/16','--','--','Kit de Fixation');
INSERT INTO "order_items" VALUES(13,7,11,1,2000,1800,3600000,'202506','06/2025','06/2030','Gants de soins');
INSERT INTO "order_items" VALUES(14,7,12,2,300,2000,600000,'--','--','--','Masques chirurgicaux');
INSERT INTO "order_items" VALUES(15,8,13,1,100,4000,400000,'--','--','--','Manche de Bistouri');
INSERT INTO "order_items" VALUES(16,8,14,2,2,230000,460000,'--','--','--','Ensemble plombé Boite');
INSERT INTO "order_items" VALUES(17,9,15,1,1,20000,20000,NULL,NULL,NULL,'Ballon respiration manuel');
INSERT INTO "order_items" VALUES(18,9,7,2,1,30000,30000,NULL,NULL,NULL,'Gants pour invasion utérine');
INSERT INTO "order_items" VALUES(19,9,2,3,50,3200,160000,NULL,NULL,NULL,'Drap d''accouchement avec poche de recueil post partum');
INSERT INTO "order_items" VALUES(20,10,16,1,30,1200,36000,NULL,NULL,NULL,'Masque nébuliseur adulte');
INSERT INTO "order_items" VALUES(21,10,17,2,18,1200,22600,NULL,NULL,NULL,'Masque nébuliseur enfant');
INSERT INTO "order_items" VALUES(22,10,18,3,2,1200,2400,NULL,NULL,NULL,'Masque nébuliseur Néonatale');
INSERT INTO "order_items" VALUES(23,11,19,1,2,250000,500000,NULL,NULL,NULL,'Déshumidificateur');
INSERT INTO "order_items" VALUES(24,12,20,1,20,14000,280000,NULL,NULL,NULL,'Valves d''Heimlich double');
INSERT INTO "order_items" VALUES(25,12,21,2,10,8000,80000,NULL,NULL,NULL,'Valves d''Heimlich Simple');
INSERT INTO "order_items" VALUES(26,13,20,1,20,14000,280000,NULL,NULL,NULL,'Valves d''Heimlich double');
INSERT INTO "order_items" VALUES(27,14,22,1,10,18000,180000,NULL,NULL,NULL,'Papier ECG 280*210 - 200 pages');
INSERT INTO "order_items" VALUES(28,14,23,2,10,9000,90000,NULL,NULL,NULL,'Papier ECG 295*210 - 100 pages');
INSERT INTO "order_items" VALUES(29,15,21,1,10,8000,80000,NULL,NULL,NULL,'Valves d''Heimlich Simple');
INSERT INTO "order_items" VALUES(30,16,24,1,20,5000,100000,NULL,NULL,NULL,'Kit de Traction Adulte');
INSERT INTO "order_items" VALUES(31,16,25,2,10,5000,50000,NULL,NULL,NULL,'Kit de Traction Enfant');
INSERT INTO "order_items" VALUES(32,17,26,1,200,3500,700000,NULL,NULL,NULL,'Drap d’accouchement avec poche de recueil post partum');
INSERT INTO "order_items" VALUES(33,17,27,2,200,140,28000,NULL,NULL,NULL,'Robinet 3 voies');
INSERT INTO "order_items" VALUES(34,17,28,3,200,360,72000,NULL,NULL,NULL,'Prolongateur 75 à 100 cm');
INSERT INTO "order_items" VALUES(35,18,29,1,5,36000,180000,NULL,NULL,NULL,'Bandelettes Fluorescéine B/50');
INSERT INTO "order_items" VALUES(36,19,30,1,1,412400,412400,NULL,NULL,NULL,'Cable vidéo Olympus MD148');
INSERT INTO "order_items" VALUES(37,20,24,1,20,5000,100000,NULL,NULL,NULL,'Kit de Traction Adulte');
INSERT INTO "order_items" VALUES(38,20,25,2,20,5000,100000,NULL,NULL,NULL,'Kit de Traction Enfant');
INSERT INTO "order_items" VALUES(39,20,7,3,400,650,260000,NULL,NULL,NULL,'Gants pour invasion utérine');
INSERT INTO "order_items" VALUES(40,21,31,1,10,8500,85000,NULL,NULL,NULL,'Rouleau papier ECG 210mmX20m');
INSERT INTO "order_items" VALUES(41,22,32,1,1,4000000,4000000,NULL,NULL,NULL,'Echobiometrie Scan AB');
INSERT INTO "order_items" VALUES(42,23,26,1,20,3200,64000,NULL,NULL,NULL,'Drap d’accouchement avec poche de recueil post partum');
INSERT INTO "order_items" VALUES(43,23,1,2,1000,150,150000,NULL,NULL,NULL,'Gants Stériles T 7,5');
INSERT INTO "order_items" VALUES(44,23,33,3,900,60,54000,NULL,NULL,NULL,'Electrode');
INSERT INTO "order_items" VALUES(45,23,7,4,100,650,65000,NULL,NULL,NULL,'Gants pour invasion utérine');
INSERT INTO "order_items" VALUES(46,24,34,1,40,50000,2000000,NULL,NULL,NULL,'Kit pour cataracte');
INSERT INTO "order_items" VALUES(47,24,35,2,20,16000,320000,NULL,NULL,NULL,'Boite de bandelettes fluorescéine');
INSERT INTO "order_items" VALUES(48,25,36,1,100,5500,550000,NULL,NULL,NULL,'Aiguille de bloc nerveux 22G Échogène - 80 mm');
INSERT INTO "order_items" VALUES(49,25,37,2,100,5500,550000,NULL,NULL,NULL,'Aiguille de bloc nerveux 22G Échogène - 100 mm');
INSERT INTO "order_items" VALUES(50,26,38,1,4,35000,140000,NULL,NULL,NULL,'Turbine à deux trous');
INSERT INTO "order_items" VALUES(51,27,3,1,1,510000,510000,NULL,NULL,NULL,'Réfrigérateur médical 400L');
INSERT INTO "order_items" VALUES(52,28,39,1,90,3000,270000,NULL,NULL,NULL,'Electrode B/50');
INSERT INTO "order_items" VALUES(53,29,36,1,100,5500,550000,NULL,NULL,NULL,'Aiguille de bloc nerveux 22G Échogène - 80 mm');
INSERT INTO "order_items" VALUES(54,29,37,2,100,5500,550000,NULL,NULL,NULL,'Aiguille de bloc nerveux 22G Échogène - 100 mm');
INSERT INTO "order_items" VALUES(55,30,3,1,1,510000,510000,NULL,NULL,NULL,'Réfrigérateur médical 400L');
INSERT INTO "order_items" VALUES(56,31,40,1,1,60000,60000,NULL,NULL,NULL,'Matelas anti-escarres');
INSERT INTO "order_items" VALUES(57,32,26,1,300,3500,1050000,NULL,NULL,NULL,'Drap d’accouchement avec poche de recueil post partum');
INSERT INTO "order_items" VALUES(58,32,1,2,1000,150,150000,NULL,NULL,NULL,'Gants Stériles T 7,5');
INSERT INTO "order_items" VALUES(59,32,7,3,400,650,260000,NULL,NULL,NULL,'Gants pour invasion utérine');
INSERT INTO "order_items" VALUES(60,33,41,1,100,3500,350000,NULL,NULL,NULL,'Manche de bistouri électrique');
INSERT INTO "order_items" VALUES(61,33,42,2,10,10000,100000,NULL,NULL,NULL,'Papier echographie UPP-110-HG');
INSERT INTO "order_items" VALUES(62,34,43,1,1,2300000,2300000,NULL,NULL,NULL,'Table opératoire électrique');
INSERT INTO "order_items" VALUES(63,35,9,1,11,11500,126500,NULL,NULL,NULL,'Surgicel');
INSERT INTO "order_items" VALUES(64,35,44,2,5,20000,100000,NULL,NULL,NULL,'Sinapi');
INSERT INTO "order_items" VALUES(65,35,45,3,10,13500,135000,NULL,NULL,NULL,'Aiguille de biopsie 16G 200mm');
INSERT INTO "order_items" VALUES(66,36,34,1,40,50000,2000000,NULL,NULL,NULL,'Kit pour cataracte');
INSERT INTO "order_items" VALUES(67,36,35,2,20,16000,320000,NULL,NULL,NULL,'Boite de bandelettes fluorescéine');
INSERT INTO "order_items" VALUES(68,37,36,1,100,5500,550000,NULL,NULL,NULL,'Aiguille de bloc nerveux 22G Échogène - 80 mm');
INSERT INTO "order_items" VALUES(69,37,37,2,100,5500,550000,NULL,NULL,NULL,'Aiguille de bloc nerveux 22G Échogène - 100 mm');
INSERT INTO "order_items" VALUES(70,38,46,1,10,5000,50000,NULL,NULL,NULL,'Implant souple avec injecteur D19');
INSERT INTO "order_items" VALUES(71,38,47,2,10,5000,50000,NULL,NULL,NULL,'Implant souple avec injecteur D20');
INSERT INTO "order_items" VALUES(72,38,48,3,20,5000,100000,NULL,NULL,NULL,'Implant souple avec injecteur D21');
INSERT INTO "order_items" VALUES(73,38,49,4,20,5000,100000,NULL,NULL,NULL,'Implant souple avec injecteur D22');
INSERT INTO "order_items" VALUES(74,38,50,5,15,5000,75000,NULL,NULL,NULL,'Implant souple avec injecteur D23');
INSERT INTO "order_items" VALUES(75,38,51,6,10,5000,50000,NULL,NULL,NULL,'Implant souple avec injecteur D24');
INSERT INTO "order_items" VALUES(76,38,52,7,10,5000,50000,NULL,NULL,NULL,'Implant souple avec injecteur D25');
INSERT INTO "order_items" VALUES(77,38,53,8,100,4000,400000,NULL,NULL,NULL,'Visqueux Lourd');
INSERT INTO "order_items" VALUES(78,38,54,9,25,10000,250000,NULL,NULL,NULL,'Couteaux 3.2');
INSERT INTO "order_items" VALUES(79,38,55,10,25,10000,250000,NULL,NULL,NULL,'Couteaux 15');
INSERT INTO "order_items" VALUES(80,38,56,11,25,10000,250000,NULL,NULL,NULL,'couteaux crescent');
INSERT INTO "order_items" VALUES(81,39,31,1,10,8500,85000,NULL,NULL,NULL,'Rouleau papier ECG 210mmX20m');
INSERT INTO "order_items" VALUES(82,40,20,1,20,14000,280000,NULL,NULL,NULL,'Valves d''Heimlich double');
INSERT INTO "order_items" VALUES(83,40,21,2,10,8000,80000,NULL,NULL,NULL,'Valves d''Heimlich simple');
INSERT INTO "order_items" VALUES(84,40,57,3,30,20000,600000,NULL,NULL,NULL,'Valves Sinapi');
INSERT INTO "order_items" VALUES(85,41,58,1,4,360000,1440000,NULL,NULL,NULL,'Cassette mammographie Fujifilm 18x24');
INSERT INTO "order_items" VALUES(86,41,59,2,4,360000,1440000,NULL,NULL,NULL,'Cassette mammographie Fujifilm 24x30');
INSERT INTO "order_items" VALUES(87,42,60,1,5000,300,1500000,NULL,NULL,NULL,'BANDE DE CREPE 10CM');
INSERT INTO "order_items" VALUES(88,42,61,2,100,400,40000,NULL,NULL,NULL,'BANDE DE CREPE 15CM');
INSERT INTO "order_items" VALUES(89,42,62,3,1000,300,300000,NULL,NULL,NULL,'SOFT BANDAGE 10CM');
INSERT INTO "order_items" VALUES(90,42,63,4,500,6500,3250000,NULL,NULL,NULL,'GANTS DE CHIRURGIE STERILES 7.5');
INSERT INTO "order_items" VALUES(91,42,64,5,500,6500,3250000,NULL,NULL,NULL,'GANTS DE CHIRURGIE STERILES 8 8.5');
INSERT INTO "order_items" VALUES(92,42,65,6,50,32500,1625000,NULL,NULL,NULL,'GANTS POUR INVASION UTERINE');
INSERT INTO "order_items" VALUES(93,42,66,7,1000,2000,2000000,NULL,NULL,NULL,'BONNET DE BLOC OPERATOIRE A USAGE UNIQUE');
INSERT INTO "order_items" VALUES(94,42,67,8,1000,1000,1000000,NULL,NULL,NULL,'COUVRE CHAUSSURES DE BLOC A USAGE UNIQUE');
INSERT INTO "order_items" VALUES(95,42,68,9,3000,9860,29580000,NULL,NULL,NULL,'KIT OPÉRATOIRE (2 CASAQUES 4 CHAMPS OPERATOIRES 2 BONNETS 2 MASQUES 2 COUVRE CHAUSSURES 2 PAIRES DE GANTS STÉRILES');
INSERT INTO "order_items" VALUES(96,42,69,10,3000,1400,4200000,NULL,NULL,NULL,'CASAQUE RENFORCÉE XL STÉRILE');
INSERT INTO "order_items" VALUES(97,42,70,11,3000,1500,4500000,NULL,NULL,NULL,'CASAQUE RENFORCÉE XXL STÉRILE');
INSERT INTO "order_items" VALUES(98,42,71,12,6000,6500,39000000,NULL,NULL,NULL,'CHAMP OPÉRATOIRE STANDARD STÉRILE 5 ÉLÉMENTS');
INSERT INTO "order_items" VALUES(99,42,72,13,30,13500,405000,NULL,NULL,NULL,'CIRE À OS EN KG');
INSERT INTO "order_items" VALUES(100,42,73,14,10000,530,5300000,NULL,NULL,NULL,'BLOUSE NON STÉRILE À USAGE UNIQUE POUR PATIENT');
INSERT INTO "order_items" VALUES(101,42,74,15,1000,2000,2000000,NULL,NULL,NULL,'MASQUES DE CHIRURGIE À USAGE UNIQUE');
INSERT INTO "order_items" VALUES(102,42,75,16,15000,1800,27000000,NULL,NULL,NULL,'GANT D’EXAMEN MM');
INSERT INTO "order_items" VALUES(103,42,76,17,2000,6500,13000000,NULL,NULL,NULL,'PIÈCES DE GAZE 100X65CM');
INSERT INTO "order_items" VALUES(104,42,77,18,1000,2800,2800000,NULL,NULL,NULL,'COTON HYDROPHILE');
INSERT INTO "order_items" VALUES(105,42,78,19,500,700,350000,NULL,NULL,NULL,'BLOUSE D’ISOLATION À USAGE UNIQUE');
INSERT INTO "order_items" VALUES(106,42,79,20,50,2800,140000,NULL,NULL,NULL,'COTON CHIRURGICAL');
INSERT INTO "order_items" VALUES(107,42,9,21,50,13985,699250,NULL,NULL,NULL,'SURGICEL');
INSERT INTO "order_items" VALUES(108,42,80,22,100,4635,463500,NULL,NULL,NULL,'ELASTOPLAST 10 CM');
INSERT INTO "order_items" VALUES(109,42,81,23,500,4800,2400000,NULL,NULL,NULL,'HYPAFIX 10CM');
INSERT INTO "order_items" VALUES(110,42,82,24,1000,1800,1800000,NULL,NULL,NULL,'SPARADRAP 5x18CM');
INSERT INTO "order_items" VALUES(111,42,83,25,200,7500,1500000,NULL,NULL,NULL,'FILM TRANSPARENT');
INSERT INTO "order_items" VALUES(112,42,84,26,250,10985,2746250,NULL,NULL,NULL,'KITS DE FIXATION');
INSERT INTO "order_items" VALUES(113,43,32,1,1,4000000,4000000,NULL,NULL,NULL,'Echobiometrie Scan AB');
INSERT INTO "order_items" VALUES(114,44,85,1,1,1200000,1200000,NULL,NULL,NULL,'Lampe à fente avec table');
INSERT INTO "order_items" VALUES(115,44,86,2,1,300000,300000,NULL,NULL,NULL,'Appareil de consultation gyneco');
INSERT INTO "order_items" VALUES(116,44,87,3,1,1900000,1900000,NULL,NULL,NULL,'Microscope opératoire');
INSERT INTO "order_items" VALUES(117,44,88,4,1,170000,170000,NULL,NULL,NULL,'Table de consultation gyneco');
INSERT INTO "order_items" VALUES(118,44,89,5,1,1300000,1300000,NULL,NULL,NULL,'Appareil d''échographie portable');
INSERT INTO "order_items" VALUES(119,44,90,6,1,120000,120000,NULL,NULL,NULL,'Malette de correction');
INSERT INTO "order_items" VALUES(120,44,91,7,1,200000,200000,NULL,NULL,NULL,'Vision chart digital avec ecrant led');
INSERT INTO "order_items" VALUES(121,45,92,1,5,31500,157500,NULL,NULL,NULL,'Pince écartante');
INSERT INTO "order_items" VALUES(122,45,93,2,5,27000,135000,NULL,NULL,NULL,'Guide sonde');
INSERT INTO "order_items" VALUES(123,45,94,3,5,40500,202500,NULL,NULL,NULL,'Mandrin d''Echman');
INSERT INTO "order_items" VALUES(124,45,95,4,5,9000,45000,NULL,NULL,NULL,'Ciseau à plâtre');
INSERT INTO "order_items" VALUES(125,45,96,5,5,9000,45000,NULL,NULL,NULL,'Davier articulaire');
INSERT INTO "order_items" VALUES(126,45,97,6,5,31500,157500,NULL,NULL,NULL,'Davier de lambotte');
INSERT INTO "order_items" VALUES(127,45,98,7,5,13500,67500,NULL,NULL,NULL,'Davier de Verbrugge à crémaillère GM et M');
INSERT INTO "order_items" VALUES(128,45,99,8,5,36000,180000,NULL,NULL,NULL,'Fer à courber les plaques');
INSERT INTO "order_items" VALUES(129,45,100,9,5,49500,247500,NULL,NULL,NULL,'Pince coupe fil');
INSERT INTO "order_items" VALUES(130,45,101,10,5,175500,877500,NULL,NULL,NULL,'Presse à courber les plaques');
INSERT INTO "order_items" VALUES(131,46,34,1,40,50000,2000000,NULL,NULL,NULL,'Kit pour cataracte');
INSERT INTO "order_items" VALUES(132,46,35,2,20,16000,320000,NULL,NULL,NULL,'Boite de bandelettes fluorescéine');
INSERT INTO "order_items" VALUES(133,47,43,1,1,2300000,2300000,NULL,NULL,NULL,'Table opératoire électrique');
INSERT INTO "order_items" VALUES(134,47,102,2,5,50000,250000,NULL,NULL,NULL,'Chaises de bloc opératoire');
INSERT INTO "order_items" VALUES(135,47,103,3,2,135000,270000,NULL,NULL,NULL,'Table mayo pour instruments');
INSERT INTO "order_items" VALUES(136,47,104,4,1,300000,300000,NULL,NULL,NULL,'Table motorisée pour auto réfractomètre');
INSERT INTO "order_items" VALUES(137,47,105,5,1,120000,120000,NULL,NULL,NULL,'Boîte de cataracte');
INSERT INTO "order_items" VALUES(138,47,106,6,1,110000,110000,NULL,NULL,NULL,'Boîte de chalazion');
INSERT INTO "order_items" VALUES(139,47,107,7,1,110000,110000,NULL,NULL,NULL,'Boîte de ptérygion');
INSERT INTO "order_items" VALUES(140,47,108,8,1,100000,100000,NULL,NULL,NULL,'Boîte de microchirurgie');
INSERT INTO "order_items" VALUES(141,47,109,9,1,120000,120000,NULL,NULL,NULL,'Valise de verres à essai');
INSERT INTO "order_items" VALUES(142,47,110,10,1,350000,350000,NULL,NULL,NULL,'Test acuité visuel avec grand écran LED');
INSERT INTO "order_items" VALUES(143,48,111,1,20,1500,30000,NULL,NULL,NULL,'Couteau crescent');
INSERT INTO "order_items" VALUES(144,48,112,2,20,1500,30000,NULL,NULL,NULL,'Couteau Keratome');
INSERT INTO "order_items" VALUES(145,48,113,3,12,4000,48000,NULL,NULL,NULL,'Visqueux');
INSERT INTO "order_items" VALUES(146,48,114,4,20,4000,80000,NULL,NULL,NULL,'Implant');
INSERT INTO "order_items" VALUES(147,49,115,1,1,2300000,2300000,NULL,NULL,NULL,'Réfractomètre');
INSERT INTO "order_items" VALUES(148,49,90,2,1,120000,120000,NULL,NULL,NULL,'Malette de correction');
INSERT INTO "order_items" VALUES(149,49,116,3,1,250000,250000,NULL,NULL,NULL,'Tableau AV ou Logiciel');
CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  client_id INTEGER NOT NULL,
  invoice_number TEXT,
  document_type TEXT NOT NULL,
  order_date TEXT,
  total_amount NUMERIC,
  source_file TEXT,
  FOREIGN KEY (client_id) REFERENCES clients(id)
);
INSERT INTO "orders" VALUES(1,1,'25/11/03','proforma','2025-11-27',1175000,'FACTURE  N◦2025_11_03.docx');
INSERT INTO "orders" VALUES(2,2,'2025/08/08','facture','2025-08-31',520000,'FACTURE No 2025_08_08.docx');
INSERT INTO "orders" VALUES(3,3,'2025/08/09','facture','2025-08-31',420000,'FACTURE No 2025_08_09.docx');
INSERT INTO "orders" VALUES(4,4,'2025/09/05','facture','2025-09-23',180000,'FACTURE No 2025_09_05.docx');
INSERT INTO "orders" VALUES(5,1,'2025/11/02','facture','2025-11-07',300000,'FACTURE No 2025_11_02.docx');
INSERT INTO "orders" VALUES(6,5,'2025/11/03','facture','2025-11-03',15706250,'FACTURE No 2025_11_03.docx');
INSERT INTO "orders" VALUES(7,5,'2025/11/05','facture','2025-11-20',4200000,'FACTURE No 2025_11_05.docx');
INSERT INTO "orders" VALUES(8,6,'2025/11/06','facture','2025-11-03',NULL,'FACTURE No 2025_11_06.docx');
INSERT INTO "orders" VALUES(9,7,'2025/12/01','facture','2025-12-10',210000,'FACTURE No 2025_12_01.docx');
INSERT INTO "orders" VALUES(10,7,'2025/12/02','facture','2025-12-15',60000,'FACTURE No 2025_12_02.docx');
INSERT INTO "orders" VALUES(11,8,'2025/12/04','facture','2025-12-18',500000,'FACTURE No 2025_12_04.docx');
INSERT INTO "orders" VALUES(12,9,'2026/01/01','facture','2026-01-14',360000,'FACTURE No 2026_01_01.docx');
INSERT INTO "orders" VALUES(13,1,'2026/01/02','facture','2026-01-14',280000,'FACTURE No 2026_01_02.docx');
INSERT INTO "orders" VALUES(14,1,'2026/01/03','facture','2026-01-14',270000,'FACTURE No 2026_01_03.docx');
INSERT INTO "orders" VALUES(15,9,'2026/01/04','facture','2026-01-21',80000,'FACTURE No 2026_01_04.docx');
INSERT INTO "orders" VALUES(16,1,'2026/01/05','facture','2026-01-23',150000,'FACTURE No 2026_01_05.docx');
INSERT INTO "orders" VALUES(17,1,'2026/02/01','facture','2026-02-17',800000,'FACTURE No 2026_02_01.docx');
INSERT INTO "orders" VALUES(18,8,'2025/09/05','facture','2025-09-23',180000,'FACTURE No 2026_02_03.docx');
INSERT INTO "orders" VALUES(19,1,'2026/03/01','facture','2026-03-10',412400,'FACTURE No 2026_03_01.docx');
INSERT INTO "orders" VALUES(20,1,'2026/03/02','facture','2026-03-10',460000,'FACTURE No 2026_03_02.docx');
INSERT INTO "orders" VALUES(21,10,'26/03/03','facture','2026-03-23',85000,'FACTURE No 2026_03_03.docx');
INSERT INTO "orders" VALUES(22,11,'2026/03/04','facture','2026-03-30',4000000,'FACTURE No 2026_03_04.docx');
INSERT INTO "orders" VALUES(23,7,'2026/05/01','proforma','2026-05-01',333000,'FACTURE No 2026_05_01.docx');
INSERT INTO "orders" VALUES(24,12,'2026/05/02','proforma','2026-05-03',2320000,'FACTURE No 2026_05_02.docx');
INSERT INTO "orders" VALUES(25,13,'2026/05/03','proforma','2026-05-06',1100000,'FACTURE No 2026_05_03.docx');
INSERT INTO "orders" VALUES(26,14,'2026/05/04','proforma','2026-05-04',140000,'FACTURE No 2026_05_04.docx');
INSERT INTO "orders" VALUES(27,15,'26/03/05','proforma','2026-03-31',510000,'FACTURE N◦26_03_05.docx');
INSERT INTO "orders" VALUES(28,16,'26/04/01','proforma','2026-04-07',270000,'FACTURE N◦26_04_01.docx');
INSERT INTO "orders" VALUES(29,16,'26/04/02','proforma','2026-04-07',1100000,'FACTURE N◦26_04_02.docx');
INSERT INTO "orders" VALUES(30,17,'26/04/03','proforma','2026-04-07',510000,'FACTURE N◦26_04_03.docx');
INSERT INTO "orders" VALUES(31,17,'26/04/04','proforma','2026-04-07',60000,'FACTURE N◦26_04_04.docx');
INSERT INTO "orders" VALUES(32,1,'26/04/05','proforma','2026-04-13',1360000,'FACTURE N◦26_04_05.docx');
INSERT INTO "orders" VALUES(33,1,'26/04/06','proforma','2026-04-13',450000,'FACTURE N◦26_04_06.docx');
INSERT INTO "orders" VALUES(34,18,'26/04/08','proforma','2026-04-27',2300000,'FACTURE N◦26_04_08.docx');
INSERT INTO "orders" VALUES(35,1,'26/04/09','proforma','2026-04-29',361500,'FACTURE N◦26_04_09.docx');
INSERT INTO "orders" VALUES(36,12,'26/04/10','proforma','2026-04-19',2320000,'FACTURE N◦26_04_10.docx');
INSERT INTO "orders" VALUES(37,16,'26/04/02','proforma','2026-04-07',1100000,'FACTURE N◦26_05_04.docx');
INSERT INTO "orders" VALUES(38,19,'25/12/12','proforma','2025-12-27',1625000,'PROFORMAT  EDA.docx');
INSERT INTO "orders" VALUES(39,10,'26/03/03','proforma','2026-03-23',85000,'PROFORMAT  NDIOUM.docx');
INSERT INTO "orders" VALUES(40,20,'26/01/05','proforma','2026-01-20',960000,'PROFORMAT  OUROSSOGUI.docx');
INSERT INTO "orders" VALUES(41,21,'25/12/03','proforma','2025-12-11',2880000,'PROFORMAT  Touba.docx');
INSERT INTO "orders" VALUES(42,5,'26/01/05','proforma','2025-12-27',178001820,'PROFORMAT  chr Saint_Louis_.docx');
INSERT INTO "orders" VALUES(43,11,'26/02/11','proforma','2026-02-23',4000000,'PROFORMAT.docx');
INSERT INTO "orders" VALUES(44,22,'26/04/08','proforma','2026-04-15',5190000,'PROFORMAT_.docx');
INSERT INTO "orders" VALUES(45,12,'26/04/09','proforma','2026-04-19',2115000,'PROFORMAT_2.docx');
INSERT INTO "orders" VALUES(46,12,'26/04/09','proforma','2026-04-19',2320000,'PROFORMAT_3.docx');
INSERT INTO "orders" VALUES(47,23,'26/04/09','proforma','2026-04-20',4030000,'PROFORMAT_Bambey.docx');
INSERT INTO "orders" VALUES(48,24,'26/02/13','proforma','2026-02-27',188000,'PROFORMAT_CS_TOUBA.docx');
INSERT INTO "orders" VALUES(49,25,'26/01/01','proforma','2026-01-06',2670000,'PROFORMAT_Touba.docx');
CREATE TABLE product_aliases (
  id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL,
  alias TEXT NOT NULL,
  normalized_alias TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'factures_zip',
  UNIQUE(product_id, normalized_alias),
  FOREIGN KEY (product_id) REFERENCES products(id)
);
INSERT INTO "product_aliases" VALUES(1,45,'Aiguille de biopsie 16G 200mm','aiguille de biopsie 16g 200mm','factures_zip');
INSERT INTO "product_aliases" VALUES(2,37,'Aiguille de bloc nerveux 22G Échogène - 100 mm','aiguille de bloc nerveux 22g echogene 100 mm','factures_zip');
INSERT INTO "product_aliases" VALUES(3,36,'Aiguille de bloc nerveux 22G Échogène - 80 mm','aiguille de bloc nerveux 22g echogene 80 mm','factures_zip');
INSERT INTO "product_aliases" VALUES(4,89,'Appareil d''échographie portable','appareil d echographie portable','factures_zip');
INSERT INTO "product_aliases" VALUES(5,86,'Appareil de consultation gyneco','appareil de consultation gyneco','factures_zip');
INSERT INTO "product_aliases" VALUES(6,60,'BANDE DE CREPE 10CM','bande de crepe 10cm','factures_zip');
INSERT INTO "product_aliases" VALUES(7,61,'BANDE DE CREPE 15CM','bande de crepe 15cm','factures_zip');
INSERT INTO "product_aliases" VALUES(8,78,'BLOUSE D’ISOLATION À USAGE UNIQUE','blouse d isolation a usage unique','factures_zip');
INSERT INTO "product_aliases" VALUES(9,73,'BLOUSE NON STÉRILE À USAGE UNIQUE POUR PATIENT','blouse non sterile a usage unique pour patient','factures_zip');
INSERT INTO "product_aliases" VALUES(10,66,'BONNET DE BLOC OPERATOIRE A USAGE UNIQUE','bonnet de bloc operatoire a usage unique','factures_zip');
INSERT INTO "product_aliases" VALUES(11,15,'Ballon respiration manuel','ballon respiration manuel','factures_zip');
INSERT INTO "product_aliases" VALUES(12,5,'Bandelettes Fluorescéine 8/50','bandelettes fluoresceine 8 50','factures_zip');
INSERT INTO "product_aliases" VALUES(13,29,'Bandelettes Fluorescéine B/50','bandelettes fluoresceine b 50','factures_zip');
INSERT INTO "product_aliases" VALUES(14,35,'Boite de bandelettes fluorescéine','boite de bandelettes fluoresceine','factures_zip');
INSERT INTO "product_aliases" VALUES(15,105,'Boîte de cataracte','boite de cataracte','factures_zip');
INSERT INTO "product_aliases" VALUES(16,106,'Boîte de chalazion','boite de chalazion','factures_zip');
INSERT INTO "product_aliases" VALUES(17,108,'Boîte de microchirurgie','boite de microchirurgie','factures_zip');
INSERT INTO "product_aliases" VALUES(18,107,'Boîte de ptérygion','boite de pterygion','factures_zip');
INSERT INTO "product_aliases" VALUES(19,69,'CASAQUE RENFORCÉE XL STÉRILE','casaque renforcee xl sterile','factures_zip');
INSERT INTO "product_aliases" VALUES(20,70,'CASAQUE RENFORCÉE XXL STÉRILE','casaque renforcee xxl sterile','factures_zip');
INSERT INTO "product_aliases" VALUES(21,71,'CHAMP OPÉRATOIRE STANDARD STÉRILE 5 ÉLÉMENTS','champ operatoire standard sterile 5 elements','factures_zip');
INSERT INTO "product_aliases" VALUES(22,72,'CIRE À OS EN KG','cire a os en kg','factures_zip');
INSERT INTO "product_aliases" VALUES(23,79,'COTON CHIRURGICAL','coton chirurgical','factures_zip');
INSERT INTO "product_aliases" VALUES(24,77,'COTON HYDROPHILE','coton hydrophile','factures_zip');
INSERT INTO "product_aliases" VALUES(25,67,'COUVRE CHAUSSURES DE BLOC A USAGE UNIQUE','couvre chaussures de bloc a usage unique','factures_zip');
INSERT INTO "product_aliases" VALUES(26,30,'Cable vidéo Olympus MD148','cable video olympus md148','factures_zip');
INSERT INTO "product_aliases" VALUES(27,58,'Cassette mammographie Fujifilm 18x24','cassette mammographie fujifilm 18x24','factures_zip');
INSERT INTO "product_aliases" VALUES(28,59,'Cassette mammographie Fujifilm 24x30','cassette mammographie fujifilm 24x30','factures_zip');
INSERT INTO "product_aliases" VALUES(29,102,'Chaises de bloc opératoire','chaises de bloc operatoire','factures_zip');
INSERT INTO "product_aliases" VALUES(30,95,'Ciseau à plâtre','ciseau a platre','factures_zip');
INSERT INTO "product_aliases" VALUES(31,112,'Couteau Keratome','couteau keratome','factures_zip');
INSERT INTO "product_aliases" VALUES(32,111,'Couteau crescent','couteau crescent','factures_zip');
INSERT INTO "product_aliases" VALUES(33,55,'Couteaux 15','couteaux 15','factures_zip');
INSERT INTO "product_aliases" VALUES(34,54,'Couteaux 3.2','couteaux 3 2','factures_zip');
INSERT INTO "product_aliases" VALUES(35,96,'Davier articulaire','davier articulaire','factures_zip');
INSERT INTO "product_aliases" VALUES(36,98,'Davier de Verbrugge à crémaillère GM et M','davier de verbrugge a cremaillere gm et m','factures_zip');
INSERT INTO "product_aliases" VALUES(37,97,'Davier de lambotte','davier de lambotte','factures_zip');
INSERT INTO "product_aliases" VALUES(38,2,'Drap d''accouchement avec poche de recueil post partum','drap d accouchement avec poche de recueil post partum','factures_zip');
INSERT INTO "product_aliases" VALUES(39,26,'Drap d’accouchement avec poche de recueil post partum','drap d accouchement avec poche de recueil post partum','factures_zip');
INSERT INTO "product_aliases" VALUES(40,19,'Déshumidificateur','deshumidificateur','factures_zip');
INSERT INTO "product_aliases" VALUES(41,80,'ELASTOPLAST 10 CM','elastoplast 10 cm','factures_zip');
INSERT INTO "product_aliases" VALUES(42,32,'Echobiometrie Scan AB','echobiometrie scan ab','factures_zip');
INSERT INTO "product_aliases" VALUES(43,33,'Electrode','electrode','factures_zip');
INSERT INTO "product_aliases" VALUES(44,39,'Electrode B/50','electrode b 50','factures_zip');
INSERT INTO "product_aliases" VALUES(45,14,'Ensemble plombé Boite','ensemble plombe boite','factures_zip');
INSERT INTO "product_aliases" VALUES(46,83,'FILM TRANSPARENT','film transparent','factures_zip');
INSERT INTO "product_aliases" VALUES(47,99,'Fer à courber les plaques','fer a courber les plaques','factures_zip');
INSERT INTO "product_aliases" VALUES(48,75,'GANT D’EXAMEN MM','gant d examen mm','factures_zip');
INSERT INTO "product_aliases" VALUES(49,63,'GANTS DE CHIRURGIE STERILES 7.5','gants de chirurgie steriles 7 5','factures_zip');
INSERT INTO "product_aliases" VALUES(50,64,'GANTS DE CHIRURGIE STERILES 8 8.5','gants de chirurgie steriles 8 8 5','factures_zip');
INSERT INTO "product_aliases" VALUES(51,65,'GANTS POUR INVASION UTERINE','gants pour invasion uterine','factures_zip');
INSERT INTO "product_aliases" VALUES(52,1,'Gants Stériles T 7,5','gants steriles t 7 5','factures_zip');
INSERT INTO "product_aliases" VALUES(53,6,'Gants Stériles T 8','gants steriles t 8','factures_zip');
INSERT INTO "product_aliases" VALUES(54,11,'Gants de soins','gants de soins','factures_zip');
INSERT INTO "product_aliases" VALUES(55,7,'Gants pour invasion utérine','gants pour invasion uterine','factures_zip');
INSERT INTO "product_aliases" VALUES(56,93,'Guide sonde','guide sonde','factures_zip');
INSERT INTO "product_aliases" VALUES(57,81,'HYPAFIX 10CM','hypafix 10cm','factures_zip');
INSERT INTO "product_aliases" VALUES(58,114,'Implant','implant','factures_zip');
INSERT INTO "product_aliases" VALUES(59,46,'Implant souple avec injecteur D19','implant souple avec injecteur d19','factures_zip');
INSERT INTO "product_aliases" VALUES(60,47,'Implant souple avec injecteur D20','implant souple avec injecteur d20','factures_zip');
INSERT INTO "product_aliases" VALUES(61,48,'Implant souple avec injecteur D21','implant souple avec injecteur d21','factures_zip');
INSERT INTO "product_aliases" VALUES(62,49,'Implant souple avec injecteur D22','implant souple avec injecteur d22','factures_zip');
INSERT INTO "product_aliases" VALUES(63,50,'Implant souple avec injecteur D23','implant souple avec injecteur d23','factures_zip');
INSERT INTO "product_aliases" VALUES(64,51,'Implant souple avec injecteur D24','implant souple avec injecteur d24','factures_zip');
INSERT INTO "product_aliases" VALUES(65,52,'Implant souple avec injecteur D25','implant souple avec injecteur d25','factures_zip');
INSERT INTO "product_aliases" VALUES(66,68,'KIT OPÉRATOIRE (2 CASAQUES 4 CHAMPS OPERATOIRES 2 BONNETS 2 MASQUES 2 COUVRE CHAUSSURES 2 PAIRES DE GANTS STÉRILES','kit operatoire 2 casaques 4 champs operatoires 2 bonnets 2 masques 2 couvre chaussures 2 paires de gants steriles','factures_zip');
INSERT INTO "product_aliases" VALUES(67,84,'KITS DE FIXATION','kits de fixation','factures_zip');
INSERT INTO "product_aliases" VALUES(68,10,'Kit de Fixation','kit de fixation','factures_zip');
INSERT INTO "product_aliases" VALUES(69,24,'Kit de Traction Adulte','kit de traction adulte','factures_zip');
INSERT INTO "product_aliases" VALUES(70,25,'Kit de Traction Enfant','kit de traction enfant','factures_zip');
INSERT INTO "product_aliases" VALUES(71,34,'Kit pour cataracte','kit pour cataracte','factures_zip');
INSERT INTO "product_aliases" VALUES(72,85,'Lampe à fente avec table','lampe a fente avec table','factures_zip');
INSERT INTO "product_aliases" VALUES(73,74,'MASQUES DE CHIRURGIE À USAGE UNIQUE','masques de chirurgie a usage unique','factures_zip');
INSERT INTO "product_aliases" VALUES(74,90,'Malette de correction','malette de correction','factures_zip');
INSERT INTO "product_aliases" VALUES(75,13,'Manche de Bistouri','manche de bistouri','factures_zip');
INSERT INTO "product_aliases" VALUES(76,41,'Manche de bistouri électrique','manche de bistouri electrique','factures_zip');
INSERT INTO "product_aliases" VALUES(77,94,'Mandrin d''Echman','mandrin d echman','factures_zip');
INSERT INTO "product_aliases" VALUES(78,18,'Masque nébuliseur Néonatale','masque nebuliseur neonatale','factures_zip');
INSERT INTO "product_aliases" VALUES(79,16,'Masque nébuliseur adulte','masque nebuliseur adulte','factures_zip');
INSERT INTO "product_aliases" VALUES(80,17,'Masque nébuliseur enfant','masque nebuliseur enfant','factures_zip');
INSERT INTO "product_aliases" VALUES(81,12,'Masques chirurgicaux','masques chirurgicaux','factures_zip');
INSERT INTO "product_aliases" VALUES(82,40,'Matelas anti-escarres','matelas anti escarres','factures_zip');
INSERT INTO "product_aliases" VALUES(83,87,'Microscope opératoire','microscope operatoire','factures_zip');
INSERT INTO "product_aliases" VALUES(84,76,'PIÈCES DE GAZE 100X65CM','pieces de gaze 100x65cm','factures_zip');
INSERT INTO "product_aliases" VALUES(85,22,'Papier ECG 280*210 - 200 pages','papier ecg 280 210 200 pages','factures_zip');
INSERT INTO "product_aliases" VALUES(86,23,'Papier ECG 295*210 - 100 pages','papier ecg 295 210 100 pages','factures_zip');
INSERT INTO "product_aliases" VALUES(87,42,'Papier echographie UPP-110-HG','papier echographie upp 110 hg','factures_zip');
INSERT INTO "product_aliases" VALUES(88,100,'Pince coupe fil','pince coupe fil','factures_zip');
INSERT INTO "product_aliases" VALUES(89,92,'Pince écartante','pince ecartante','factures_zip');
INSERT INTO "product_aliases" VALUES(90,101,'Presse à courber les plaques','presse a courber les plaques','factures_zip');
INSERT INTO "product_aliases" VALUES(91,28,'Prolongateur 75 à 100 cm','prolongateur 75 a 100 cm','factures_zip');
INSERT INTO "product_aliases" VALUES(92,27,'Robinet 3 voies','robinet 3 voies','factures_zip');
INSERT INTO "product_aliases" VALUES(93,31,'Rouleau papier ECG 210mmX20m','rouleau papier ecg 210mmx20m','factures_zip');
INSERT INTO "product_aliases" VALUES(94,115,'Réfractomètre','refractometre','factures_zip');
INSERT INTO "product_aliases" VALUES(95,4,'Réfrigérateur médical 150L','refrigerateur medical 150l','factures_zip');
INSERT INTO "product_aliases" VALUES(96,3,'Réfrigérateur médical 400L','refrigerateur medical 400l','factures_zip');
INSERT INTO "product_aliases" VALUES(97,62,'SOFT BANDAGE 10CM','soft bandage 10cm','factures_zip');
INSERT INTO "product_aliases" VALUES(98,82,'SPARADRAP 5x18CM','sparadrap 5x18cm','factures_zip');
INSERT INTO "product_aliases" VALUES(99,44,'Sinapi','sinapi','factures_zip');
INSERT INTO "product_aliases" VALUES(100,9,'Surgicel','surgicel','factures_zip');
INSERT INTO "product_aliases" VALUES(101,88,'Table de consultation gyneco','table de consultation gyneco','factures_zip');
INSERT INTO "product_aliases" VALUES(102,103,'Table mayo pour instruments','table mayo pour instruments','factures_zip');
INSERT INTO "product_aliases" VALUES(103,104,'Table motorisée pour auto réfractomètre','table motorisee pour auto refractometre','factures_zip');
INSERT INTO "product_aliases" VALUES(104,43,'Table opératoire électrique','table operatoire electrique','factures_zip');
INSERT INTO "product_aliases" VALUES(105,116,'Tableau AV ou Logiciel','tableau av ou logiciel','factures_zip');
INSERT INTO "product_aliases" VALUES(106,110,'Test acuité visuel avec grand écran LED','test acuite visuel avec grand ecran led','factures_zip');
INSERT INTO "product_aliases" VALUES(107,8,'Trousse Universelle','trousse universelle','factures_zip');
INSERT INTO "product_aliases" VALUES(108,38,'Turbine à deux trous','turbine a deux trous','factures_zip');
INSERT INTO "product_aliases" VALUES(109,109,'Valise de verres à essai','valise de verres a essai','factures_zip');
INSERT INTO "product_aliases" VALUES(110,57,'Valves Sinapi','valves sinapi','factures_zip');
INSERT INTO "product_aliases" VALUES(111,21,'Valves d''Heimlich Simple','valves d heimlich simple','factures_zip');
INSERT INTO "product_aliases" VALUES(112,20,'Valves d''Heimlich double','valves d heimlich double','factures_zip');
INSERT INTO "product_aliases" VALUES(113,91,'Vision chart digital avec ecrant led','vision chart digital avec ecrant led','factures_zip');
INSERT INTO "product_aliases" VALUES(114,113,'Visqueux','visqueux','factures_zip');
INSERT INTO "product_aliases" VALUES(115,53,'Visqueux Lourd','visqueux lourd','factures_zip');
INSERT INTO "product_aliases" VALUES(116,56,'couteaux crescent','couteaux crescent','factures_zip');
CREATE TABLE product_price_history (
  id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL,
  order_item_id INTEGER NOT NULL,
  order_id INTEGER NOT NULL,
  client_id INTEGER NOT NULL,
  price NUMERIC NOT NULL,
  quantity NUMERIC,
  line_total NUMERIC,
  order_date TEXT,
  source_file TEXT,
  source TEXT NOT NULL DEFAULT 'facture_line',
  FOREIGN KEY (product_id) REFERENCES products(id),
  FOREIGN KEY (order_item_id) REFERENCES order_items(id),
  FOREIGN KEY (order_id) REFERENCES orders(id),
  FOREIGN KEY (client_id) REFERENCES clients(id)
);
INSERT INTO "product_price_history" VALUES(1,1,1,1,1,150,2000,300000,'2025-11-27','FACTURE  N◦2025_11_03.docx','facture_line');
INSERT INTO "product_price_history" VALUES(2,2,2,1,1,3500,250,875000,'2025-11-27','FACTURE  N◦2025_11_03.docx','facture_line');
INSERT INTO "product_price_history" VALUES(3,3,3,2,2,520000,1,520000,'2025-08-31','FACTURE No 2025_08_08.docx','facture_line');
INSERT INTO "product_price_history" VALUES(4,4,4,3,3,420000,1,420000,'2025-08-31','FACTURE No 2025_08_09.docx','facture_line');
INSERT INTO "product_price_history" VALUES(5,5,5,4,4,36000,5,180000,'2025-09-23','FACTURE No 2025_09_05.docx','facture_line');
INSERT INTO "product_price_history" VALUES(6,1,6,5,1,150,2000,300000,'2025-11-07','FACTURE No 2025_11_02.docx','facture_line');
INSERT INTO "product_price_history" VALUES(7,1,7,6,5,6500,300,1950000,'2025-11-03','FACTURE No 2025_11_03.docx','facture_line');
INSERT INTO "product_price_history" VALUES(8,6,8,6,5,6500,150,975000,'2025-11-03','FACTURE No 2025_11_03.docx','facture_line');
INSERT INTO "product_price_history" VALUES(9,7,9,6,5,32500,10,325000,'2025-11-03','FACTURE No 2025_11_03.docx','facture_line');
INSERT INTO "product_price_history" VALUES(10,8,10,6,5,9860,1200,11832000,'2025-11-03','FACTURE No 2025_11_03.docx','facture_line');
INSERT INTO "product_price_history" VALUES(11,9,11,6,5,13985,25,349625,'2025-11-03','FACTURE No 2025_11_03.docx','facture_line');
INSERT INTO "product_price_history" VALUES(12,10,12,6,5,10985,25,274625,'2025-11-03','FACTURE No 2025_11_03.docx','facture_line');
INSERT INTO "product_price_history" VALUES(13,11,13,7,5,1800,2000,3600000,'2025-11-20','FACTURE No 2025_11_05.docx','facture_line');
INSERT INTO "product_price_history" VALUES(14,12,14,7,5,2000,300,600000,'2025-11-20','FACTURE No 2025_11_05.docx','facture_line');
INSERT INTO "product_price_history" VALUES(15,13,15,8,6,4000,100,400000,'2025-11-03','FACTURE No 2025_11_06.docx','facture_line');
INSERT INTO "product_price_history" VALUES(16,14,16,8,6,230000,2,460000,'2025-11-03','FACTURE No 2025_11_06.docx','facture_line');
INSERT INTO "product_price_history" VALUES(17,15,17,9,7,20000,1,20000,'2025-12-10','FACTURE No 2025_12_01.docx','facture_line');
INSERT INTO "product_price_history" VALUES(18,7,18,9,7,30000,1,30000,'2025-12-10','FACTURE No 2025_12_01.docx','facture_line');
INSERT INTO "product_price_history" VALUES(19,2,19,9,7,3200,50,160000,'2025-12-10','FACTURE No 2025_12_01.docx','facture_line');
INSERT INTO "product_price_history" VALUES(20,16,20,10,7,1200,30,36000,'2025-12-15','FACTURE No 2025_12_02.docx','facture_line');
INSERT INTO "product_price_history" VALUES(21,17,21,10,7,1200,18,22600,'2025-12-15','FACTURE No 2025_12_02.docx','facture_line');
INSERT INTO "product_price_history" VALUES(22,18,22,10,7,1200,2,2400,'2025-12-15','FACTURE No 2025_12_02.docx','facture_line');
INSERT INTO "product_price_history" VALUES(23,19,23,11,8,250000,2,500000,'2025-12-18','FACTURE No 2025_12_04.docx','facture_line');
INSERT INTO "product_price_history" VALUES(24,20,24,12,9,14000,20,280000,'2026-01-14','FACTURE No 2026_01_01.docx','facture_line');
INSERT INTO "product_price_history" VALUES(25,21,25,12,9,8000,10,80000,'2026-01-14','FACTURE No 2026_01_01.docx','facture_line');
INSERT INTO "product_price_history" VALUES(26,20,26,13,1,14000,20,280000,'2026-01-14','FACTURE No 2026_01_02.docx','facture_line');
INSERT INTO "product_price_history" VALUES(27,22,27,14,1,18000,10,180000,'2026-01-14','FACTURE No 2026_01_03.docx','facture_line');
INSERT INTO "product_price_history" VALUES(28,23,28,14,1,9000,10,90000,'2026-01-14','FACTURE No 2026_01_03.docx','facture_line');
INSERT INTO "product_price_history" VALUES(29,21,29,15,9,8000,10,80000,'2026-01-21','FACTURE No 2026_01_04.docx','facture_line');
INSERT INTO "product_price_history" VALUES(30,24,30,16,1,5000,20,100000,'2026-01-23','FACTURE No 2026_01_05.docx','facture_line');
INSERT INTO "product_price_history" VALUES(31,25,31,16,1,5000,10,50000,'2026-01-23','FACTURE No 2026_01_05.docx','facture_line');
INSERT INTO "product_price_history" VALUES(32,26,32,17,1,3500,200,700000,'2026-02-17','FACTURE No 2026_02_01.docx','facture_line');
INSERT INTO "product_price_history" VALUES(33,27,33,17,1,140,200,28000,'2026-02-17','FACTURE No 2026_02_01.docx','facture_line');
INSERT INTO "product_price_history" VALUES(34,28,34,17,1,360,200,72000,'2026-02-17','FACTURE No 2026_02_01.docx','facture_line');
INSERT INTO "product_price_history" VALUES(35,29,35,18,8,36000,5,180000,'2025-09-23','FACTURE No 2026_02_03.docx','facture_line');
INSERT INTO "product_price_history" VALUES(36,30,36,19,1,412400,1,412400,'2026-03-10','FACTURE No 2026_03_01.docx','facture_line');
INSERT INTO "product_price_history" VALUES(37,24,37,20,1,5000,20,100000,'2026-03-10','FACTURE No 2026_03_02.docx','facture_line');
INSERT INTO "product_price_history" VALUES(38,25,38,20,1,5000,20,100000,'2026-03-10','FACTURE No 2026_03_02.docx','facture_line');
INSERT INTO "product_price_history" VALUES(39,7,39,20,1,650,400,260000,'2026-03-10','FACTURE No 2026_03_02.docx','facture_line');
INSERT INTO "product_price_history" VALUES(40,31,40,21,10,8500,10,85000,'2026-03-23','FACTURE No 2026_03_03.docx','facture_line');
INSERT INTO "product_price_history" VALUES(41,32,41,22,11,4000000,1,4000000,'2026-03-30','FACTURE No 2026_03_04.docx','facture_line');
INSERT INTO "product_price_history" VALUES(42,26,42,23,7,3200,20,64000,'2026-05-01','FACTURE No 2026_05_01.docx','facture_line');
INSERT INTO "product_price_history" VALUES(43,1,43,23,7,150,1000,150000,'2026-05-01','FACTURE No 2026_05_01.docx','facture_line');
INSERT INTO "product_price_history" VALUES(44,33,44,23,7,60,900,54000,'2026-05-01','FACTURE No 2026_05_01.docx','facture_line');
INSERT INTO "product_price_history" VALUES(45,7,45,23,7,650,100,65000,'2026-05-01','FACTURE No 2026_05_01.docx','facture_line');
INSERT INTO "product_price_history" VALUES(46,34,46,24,12,50000,40,2000000,'2026-05-03','FACTURE No 2026_05_02.docx','facture_line');
INSERT INTO "product_price_history" VALUES(47,35,47,24,12,16000,20,320000,'2026-05-03','FACTURE No 2026_05_02.docx','facture_line');
INSERT INTO "product_price_history" VALUES(48,36,48,25,13,5500,100,550000,'2026-05-06','FACTURE No 2026_05_03.docx','facture_line');
INSERT INTO "product_price_history" VALUES(49,37,49,25,13,5500,100,550000,'2026-05-06','FACTURE No 2026_05_03.docx','facture_line');
INSERT INTO "product_price_history" VALUES(50,38,50,26,14,35000,4,140000,'2026-05-04','FACTURE No 2026_05_04.docx','facture_line');
INSERT INTO "product_price_history" VALUES(51,3,51,27,15,510000,1,510000,'2026-03-31','FACTURE N◦26_03_05.docx','facture_line');
INSERT INTO "product_price_history" VALUES(52,39,52,28,16,3000,90,270000,'2026-04-07','FACTURE N◦26_04_01.docx','facture_line');
INSERT INTO "product_price_history" VALUES(53,36,53,29,16,5500,100,550000,'2026-04-07','FACTURE N◦26_04_02.docx','facture_line');
INSERT INTO "product_price_history" VALUES(54,37,54,29,16,5500,100,550000,'2026-04-07','FACTURE N◦26_04_02.docx','facture_line');
INSERT INTO "product_price_history" VALUES(55,3,55,30,17,510000,1,510000,'2026-04-07','FACTURE N◦26_04_03.docx','facture_line');
INSERT INTO "product_price_history" VALUES(56,40,56,31,17,60000,1,60000,'2026-04-07','FACTURE N◦26_04_04.docx','facture_line');
INSERT INTO "product_price_history" VALUES(57,26,57,32,1,3500,300,1050000,'2026-04-13','FACTURE N◦26_04_05.docx','facture_line');
INSERT INTO "product_price_history" VALUES(58,1,58,32,1,150,1000,150000,'2026-04-13','FACTURE N◦26_04_05.docx','facture_line');
INSERT INTO "product_price_history" VALUES(59,7,59,32,1,650,400,260000,'2026-04-13','FACTURE N◦26_04_05.docx','facture_line');
INSERT INTO "product_price_history" VALUES(60,41,60,33,1,3500,100,350000,'2026-04-13','FACTURE N◦26_04_06.docx','facture_line');
INSERT INTO "product_price_history" VALUES(61,42,61,33,1,10000,10,100000,'2026-04-13','FACTURE N◦26_04_06.docx','facture_line');
INSERT INTO "product_price_history" VALUES(62,43,62,34,18,2300000,1,2300000,'2026-04-27','FACTURE N◦26_04_08.docx','facture_line');
INSERT INTO "product_price_history" VALUES(63,9,63,35,1,11500,11,126500,'2026-04-29','FACTURE N◦26_04_09.docx','facture_line');
INSERT INTO "product_price_history" VALUES(64,44,64,35,1,20000,5,100000,'2026-04-29','FACTURE N◦26_04_09.docx','facture_line');
INSERT INTO "product_price_history" VALUES(65,45,65,35,1,13500,10,135000,'2026-04-29','FACTURE N◦26_04_09.docx','facture_line');
INSERT INTO "product_price_history" VALUES(66,34,66,36,12,50000,40,2000000,'2026-04-19','FACTURE N◦26_04_10.docx','facture_line');
INSERT INTO "product_price_history" VALUES(67,35,67,36,12,16000,20,320000,'2026-04-19','FACTURE N◦26_04_10.docx','facture_line');
INSERT INTO "product_price_history" VALUES(68,36,68,37,16,5500,100,550000,'2026-04-07','FACTURE N◦26_05_04.docx','facture_line');
INSERT INTO "product_price_history" VALUES(69,37,69,37,16,5500,100,550000,'2026-04-07','FACTURE N◦26_05_04.docx','facture_line');
INSERT INTO "product_price_history" VALUES(70,46,70,38,19,5000,10,50000,'2025-12-27','PROFORMAT  EDA.docx','facture_line');
INSERT INTO "product_price_history" VALUES(71,47,71,38,19,5000,10,50000,'2025-12-27','PROFORMAT  EDA.docx','facture_line');
INSERT INTO "product_price_history" VALUES(72,48,72,38,19,5000,20,100000,'2025-12-27','PROFORMAT  EDA.docx','facture_line');
INSERT INTO "product_price_history" VALUES(73,49,73,38,19,5000,20,100000,'2025-12-27','PROFORMAT  EDA.docx','facture_line');
INSERT INTO "product_price_history" VALUES(74,50,74,38,19,5000,15,75000,'2025-12-27','PROFORMAT  EDA.docx','facture_line');
INSERT INTO "product_price_history" VALUES(75,51,75,38,19,5000,10,50000,'2025-12-27','PROFORMAT  EDA.docx','facture_line');
INSERT INTO "product_price_history" VALUES(76,52,76,38,19,5000,10,50000,'2025-12-27','PROFORMAT  EDA.docx','facture_line');
INSERT INTO "product_price_history" VALUES(77,53,77,38,19,4000,100,400000,'2025-12-27','PROFORMAT  EDA.docx','facture_line');
INSERT INTO "product_price_history" VALUES(78,54,78,38,19,10000,25,250000,'2025-12-27','PROFORMAT  EDA.docx','facture_line');
INSERT INTO "product_price_history" VALUES(79,55,79,38,19,10000,25,250000,'2025-12-27','PROFORMAT  EDA.docx','facture_line');
INSERT INTO "product_price_history" VALUES(80,56,80,38,19,10000,25,250000,'2025-12-27','PROFORMAT  EDA.docx','facture_line');
INSERT INTO "product_price_history" VALUES(81,31,81,39,10,8500,10,85000,'2026-03-23','PROFORMAT  NDIOUM.docx','facture_line');
INSERT INTO "product_price_history" VALUES(82,20,82,40,20,14000,20,280000,'2026-01-20','PROFORMAT  OUROSSOGUI.docx','facture_line');
INSERT INTO "product_price_history" VALUES(83,21,83,40,20,8000,10,80000,'2026-01-20','PROFORMAT  OUROSSOGUI.docx','facture_line');
INSERT INTO "product_price_history" VALUES(84,57,84,40,20,20000,30,600000,'2026-01-20','PROFORMAT  OUROSSOGUI.docx','facture_line');
INSERT INTO "product_price_history" VALUES(85,58,85,41,21,360000,4,1440000,'2025-12-11','PROFORMAT  Touba.docx','facture_line');
INSERT INTO "product_price_history" VALUES(86,59,86,41,21,360000,4,1440000,'2025-12-11','PROFORMAT  Touba.docx','facture_line');
INSERT INTO "product_price_history" VALUES(87,60,87,42,5,300,5000,1500000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(88,61,88,42,5,400,100,40000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(89,62,89,42,5,300,1000,300000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(90,63,90,42,5,6500,500,3250000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(91,64,91,42,5,6500,500,3250000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(92,65,92,42,5,32500,50,1625000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(93,66,93,42,5,2000,1000,2000000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(94,67,94,42,5,1000,1000,1000000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(95,68,95,42,5,9860,3000,29580000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(96,69,96,42,5,1400,3000,4200000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(97,70,97,42,5,1500,3000,4500000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(98,71,98,42,5,6500,6000,39000000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(99,72,99,42,5,13500,30,405000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(100,73,100,42,5,530,10000,5300000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(101,74,101,42,5,2000,1000,2000000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(102,75,102,42,5,1800,15000,27000000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(103,76,103,42,5,6500,2000,13000000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(104,77,104,42,5,2800,1000,2800000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(105,78,105,42,5,700,500,350000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(106,79,106,42,5,2800,50,140000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(107,9,107,42,5,13985,50,699250,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(108,80,108,42,5,4635,100,463500,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(109,81,109,42,5,4800,500,2400000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(110,82,110,42,5,1800,1000,1800000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(111,83,111,42,5,7500,200,1500000,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(112,84,112,42,5,10985,250,2746250,'2025-12-27','PROFORMAT  chr Saint_Louis_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(113,32,113,43,11,4000000,1,4000000,'2026-02-23','PROFORMAT.docx','facture_line');
INSERT INTO "product_price_history" VALUES(114,85,114,44,22,1200000,1,1200000,'2026-04-15','PROFORMAT_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(115,86,115,44,22,300000,1,300000,'2026-04-15','PROFORMAT_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(116,87,116,44,22,1900000,1,1900000,'2026-04-15','PROFORMAT_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(117,88,117,44,22,170000,1,170000,'2026-04-15','PROFORMAT_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(118,89,118,44,22,1300000,1,1300000,'2026-04-15','PROFORMAT_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(119,90,119,44,22,120000,1,120000,'2026-04-15','PROFORMAT_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(120,91,120,44,22,200000,1,200000,'2026-04-15','PROFORMAT_.docx','facture_line');
INSERT INTO "product_price_history" VALUES(121,92,121,45,12,31500,5,157500,'2026-04-19','PROFORMAT_2.docx','facture_line');
INSERT INTO "product_price_history" VALUES(122,93,122,45,12,27000,5,135000,'2026-04-19','PROFORMAT_2.docx','facture_line');
INSERT INTO "product_price_history" VALUES(123,94,123,45,12,40500,5,202500,'2026-04-19','PROFORMAT_2.docx','facture_line');
INSERT INTO "product_price_history" VALUES(124,95,124,45,12,9000,5,45000,'2026-04-19','PROFORMAT_2.docx','facture_line');
INSERT INTO "product_price_history" VALUES(125,96,125,45,12,9000,5,45000,'2026-04-19','PROFORMAT_2.docx','facture_line');
INSERT INTO "product_price_history" VALUES(126,97,126,45,12,31500,5,157500,'2026-04-19','PROFORMAT_2.docx','facture_line');
INSERT INTO "product_price_history" VALUES(127,98,127,45,12,13500,5,67500,'2026-04-19','PROFORMAT_2.docx','facture_line');
INSERT INTO "product_price_history" VALUES(128,99,128,45,12,36000,5,180000,'2026-04-19','PROFORMAT_2.docx','facture_line');
INSERT INTO "product_price_history" VALUES(129,100,129,45,12,49500,5,247500,'2026-04-19','PROFORMAT_2.docx','facture_line');
INSERT INTO "product_price_history" VALUES(130,101,130,45,12,175500,5,877500,'2026-04-19','PROFORMAT_2.docx','facture_line');
INSERT INTO "product_price_history" VALUES(131,34,131,46,12,50000,40,2000000,'2026-04-19','PROFORMAT_3.docx','facture_line');
INSERT INTO "product_price_history" VALUES(132,35,132,46,12,16000,20,320000,'2026-04-19','PROFORMAT_3.docx','facture_line');
INSERT INTO "product_price_history" VALUES(133,43,133,47,23,2300000,1,2300000,'2026-04-20','PROFORMAT_Bambey.docx','facture_line');
INSERT INTO "product_price_history" VALUES(134,102,134,47,23,50000,5,250000,'2026-04-20','PROFORMAT_Bambey.docx','facture_line');
INSERT INTO "product_price_history" VALUES(135,103,135,47,23,135000,2,270000,'2026-04-20','PROFORMAT_Bambey.docx','facture_line');
INSERT INTO "product_price_history" VALUES(136,104,136,47,23,300000,1,300000,'2026-04-20','PROFORMAT_Bambey.docx','facture_line');
INSERT INTO "product_price_history" VALUES(137,105,137,47,23,120000,1,120000,'2026-04-20','PROFORMAT_Bambey.docx','facture_line');
INSERT INTO "product_price_history" VALUES(138,106,138,47,23,110000,1,110000,'2026-04-20','PROFORMAT_Bambey.docx','facture_line');
INSERT INTO "product_price_history" VALUES(139,107,139,47,23,110000,1,110000,'2026-04-20','PROFORMAT_Bambey.docx','facture_line');
INSERT INTO "product_price_history" VALUES(140,108,140,47,23,100000,1,100000,'2026-04-20','PROFORMAT_Bambey.docx','facture_line');
INSERT INTO "product_price_history" VALUES(141,109,141,47,23,120000,1,120000,'2026-04-20','PROFORMAT_Bambey.docx','facture_line');
INSERT INTO "product_price_history" VALUES(142,110,142,47,23,350000,1,350000,'2026-04-20','PROFORMAT_Bambey.docx','facture_line');
INSERT INTO "product_price_history" VALUES(143,111,143,48,24,1500,20,30000,'2026-02-27','PROFORMAT_CS_TOUBA.docx','facture_line');
INSERT INTO "product_price_history" VALUES(144,112,144,48,24,1500,20,30000,'2026-02-27','PROFORMAT_CS_TOUBA.docx','facture_line');
INSERT INTO "product_price_history" VALUES(145,113,145,48,24,4000,12,48000,'2026-02-27','PROFORMAT_CS_TOUBA.docx','facture_line');
INSERT INTO "product_price_history" VALUES(146,114,146,48,24,4000,20,80000,'2026-02-27','PROFORMAT_CS_TOUBA.docx','facture_line');
INSERT INTO "product_price_history" VALUES(147,115,147,49,25,2300000,1,2300000,'2026-01-06','PROFORMAT_Touba.docx','facture_line');
INSERT INTO "product_price_history" VALUES(148,90,148,49,25,120000,1,120000,'2026-01-06','PROFORMAT_Touba.docx','facture_line');
INSERT INTO "product_price_history" VALUES(149,116,149,49,25,250000,1,250000,'2026-01-06','PROFORMAT_Touba.docx','facture_line');
CREATE TABLE products (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  default_unit_price NUMERIC
);
INSERT INTO "products" VALUES(1,'Gants Stériles T 7,5',150);
INSERT INTO "products" VALUES(2,'Drap d''accouchement avec poche de recueil post partum',3500);
INSERT INTO "products" VALUES(3,'Réfrigérateur médical 400L',520000);
INSERT INTO "products" VALUES(4,'Réfrigérateur médical 150L',420000);
INSERT INTO "products" VALUES(5,'Bandelettes Fluorescéine 8/50',36000);
INSERT INTO "products" VALUES(6,'Gants Stériles T 8',6500);
INSERT INTO "products" VALUES(7,'Gants pour invasion utérine',32500);
INSERT INTO "products" VALUES(8,'Trousse Universelle',9860);
INSERT INTO "products" VALUES(9,'Surgicel',13985);
INSERT INTO "products" VALUES(10,'Kit de Fixation',10985);
INSERT INTO "products" VALUES(11,'Gants de soins',1800);
INSERT INTO "products" VALUES(12,'Masques chirurgicaux',2000);
INSERT INTO "products" VALUES(13,'Manche de Bistouri',4000);
INSERT INTO "products" VALUES(14,'Ensemble plombé Boite',230000);
INSERT INTO "products" VALUES(15,'Ballon respiration manuel',20000);
INSERT INTO "products" VALUES(16,'Masque nébuliseur adulte',1200);
INSERT INTO "products" VALUES(17,'Masque nébuliseur enfant',1200);
INSERT INTO "products" VALUES(18,'Masque nébuliseur Néonatale',1200);
INSERT INTO "products" VALUES(19,'Déshumidificateur',250000);
INSERT INTO "products" VALUES(20,'Valves d''Heimlich double',14000);
INSERT INTO "products" VALUES(21,'Valves d''Heimlich Simple',8000);
INSERT INTO "products" VALUES(22,'Papier ECG 280*210 - 200 pages',18000);
INSERT INTO "products" VALUES(23,'Papier ECG 295*210 - 100 pages',9000);
INSERT INTO "products" VALUES(24,'Kit de Traction Adulte',5000);
INSERT INTO "products" VALUES(25,'Kit de Traction Enfant',5000);
INSERT INTO "products" VALUES(26,'Drap d’accouchement avec poche de recueil post partum',3500);
INSERT INTO "products" VALUES(27,'Robinet 3 voies',140);
INSERT INTO "products" VALUES(28,'Prolongateur 75 à 100 cm',360);
INSERT INTO "products" VALUES(29,'Bandelettes Fluorescéine B/50',36000);
INSERT INTO "products" VALUES(30,'Cable vidéo Olympus MD148',412400);
INSERT INTO "products" VALUES(31,'Rouleau papier ECG 210mmX20m',8500);
INSERT INTO "products" VALUES(32,'Echobiometrie Scan AB',4000000);
INSERT INTO "products" VALUES(33,'Electrode',60);
INSERT INTO "products" VALUES(34,'Kit pour cataracte',50000);
INSERT INTO "products" VALUES(35,'Boite de bandelettes fluorescéine',16000);
INSERT INTO "products" VALUES(36,'Aiguille de bloc nerveux 22G Échogène - 80 mm',5500);
INSERT INTO "products" VALUES(37,'Aiguille de bloc nerveux 22G Échogène - 100 mm',5500);
INSERT INTO "products" VALUES(38,'Turbine à deux trous',35000);
INSERT INTO "products" VALUES(39,'Electrode B/50',3000);
INSERT INTO "products" VALUES(40,'Matelas anti-escarres',60000);
INSERT INTO "products" VALUES(41,'Manche de bistouri électrique',3500);
INSERT INTO "products" VALUES(42,'Papier echographie UPP-110-HG',10000);
INSERT INTO "products" VALUES(43,'Table opératoire électrique',2300000);
INSERT INTO "products" VALUES(44,'Sinapi',20000);
INSERT INTO "products" VALUES(45,'Aiguille de biopsie 16G 200mm',13500);
INSERT INTO "products" VALUES(46,'Implant souple avec injecteur D19',5000);
INSERT INTO "products" VALUES(47,'Implant souple avec injecteur D20',5000);
INSERT INTO "products" VALUES(48,'Implant souple avec injecteur D21',5000);
INSERT INTO "products" VALUES(49,'Implant souple avec injecteur D22',5000);
INSERT INTO "products" VALUES(50,'Implant souple avec injecteur D23',5000);
INSERT INTO "products" VALUES(51,'Implant souple avec injecteur D24',5000);
INSERT INTO "products" VALUES(52,'Implant souple avec injecteur D25',5000);
INSERT INTO "products" VALUES(53,'Visqueux Lourd',4000);
INSERT INTO "products" VALUES(54,'Couteaux 3.2',10000);
INSERT INTO "products" VALUES(55,'Couteaux 15',10000);
INSERT INTO "products" VALUES(56,'couteaux crescent',10000);
INSERT INTO "products" VALUES(57,'Valves Sinapi',20000);
INSERT INTO "products" VALUES(58,'Cassette mammographie Fujifilm 18x24',360000);
INSERT INTO "products" VALUES(59,'Cassette mammographie Fujifilm 24x30',360000);
INSERT INTO "products" VALUES(60,'BANDE DE CREPE 10CM',300);
INSERT INTO "products" VALUES(61,'BANDE DE CREPE 15CM',400);
INSERT INTO "products" VALUES(62,'SOFT BANDAGE 10CM',300);
INSERT INTO "products" VALUES(63,'GANTS DE CHIRURGIE STERILES 7.5',6500);
INSERT INTO "products" VALUES(64,'GANTS DE CHIRURGIE STERILES 8 8.5',6500);
INSERT INTO "products" VALUES(65,'GANTS POUR INVASION UTERINE',32500);
INSERT INTO "products" VALUES(66,'BONNET DE BLOC OPERATOIRE A USAGE UNIQUE',2000);
INSERT INTO "products" VALUES(67,'COUVRE CHAUSSURES DE BLOC A USAGE UNIQUE',1000);
INSERT INTO "products" VALUES(68,'KIT OPÉRATOIRE (2 CASAQUES 4 CHAMPS OPERATOIRES 2 BONNETS 2 MASQUES 2 COUVRE CHAUSSURES 2 PAIRES DE GANTS STÉRILES',9860);
INSERT INTO "products" VALUES(69,'CASAQUE RENFORCÉE XL STÉRILE',1400);
INSERT INTO "products" VALUES(70,'CASAQUE RENFORCÉE XXL STÉRILE',1500);
INSERT INTO "products" VALUES(71,'CHAMP OPÉRATOIRE STANDARD STÉRILE 5 ÉLÉMENTS',6500);
INSERT INTO "products" VALUES(72,'CIRE À OS EN KG',13500);
INSERT INTO "products" VALUES(73,'BLOUSE NON STÉRILE À USAGE UNIQUE POUR PATIENT',530);
INSERT INTO "products" VALUES(74,'MASQUES DE CHIRURGIE À USAGE UNIQUE',2000);
INSERT INTO "products" VALUES(75,'GANT D’EXAMEN MM',1800);
INSERT INTO "products" VALUES(76,'PIÈCES DE GAZE 100X65CM',6500);
INSERT INTO "products" VALUES(77,'COTON HYDROPHILE',2800);
INSERT INTO "products" VALUES(78,'BLOUSE D’ISOLATION À USAGE UNIQUE',700);
INSERT INTO "products" VALUES(79,'COTON CHIRURGICAL',2800);
INSERT INTO "products" VALUES(80,'ELASTOPLAST 10 CM',4635);
INSERT INTO "products" VALUES(81,'HYPAFIX 10CM',4800);
INSERT INTO "products" VALUES(82,'SPARADRAP 5x18CM',1800);
INSERT INTO "products" VALUES(83,'FILM TRANSPARENT',7500);
INSERT INTO "products" VALUES(84,'KITS DE FIXATION',10985);
INSERT INTO "products" VALUES(85,'Lampe à fente avec table',1200000);
INSERT INTO "products" VALUES(86,'Appareil de consultation gyneco',300000);
INSERT INTO "products" VALUES(87,'Microscope opératoire',1900000);
INSERT INTO "products" VALUES(88,'Table de consultation gyneco',170000);
INSERT INTO "products" VALUES(89,'Appareil d''échographie portable',1300000);
INSERT INTO "products" VALUES(90,'Malette de correction',120000);
INSERT INTO "products" VALUES(91,'Vision chart digital avec ecrant led',200000);
INSERT INTO "products" VALUES(92,'Pince écartante',31500);
INSERT INTO "products" VALUES(93,'Guide sonde',27000);
INSERT INTO "products" VALUES(94,'Mandrin d''Echman',40500);
INSERT INTO "products" VALUES(95,'Ciseau à plâtre',9000);
INSERT INTO "products" VALUES(96,'Davier articulaire',9000);
INSERT INTO "products" VALUES(97,'Davier de lambotte',31500);
INSERT INTO "products" VALUES(98,'Davier de Verbrugge à crémaillère GM et M',13500);
INSERT INTO "products" VALUES(99,'Fer à courber les plaques',36000);
INSERT INTO "products" VALUES(100,'Pince coupe fil',49500);
INSERT INTO "products" VALUES(101,'Presse à courber les plaques',175500);
INSERT INTO "products" VALUES(102,'Chaises de bloc opératoire',50000);
INSERT INTO "products" VALUES(103,'Table mayo pour instruments',135000);
INSERT INTO "products" VALUES(104,'Table motorisée pour auto réfractomètre',300000);
INSERT INTO "products" VALUES(105,'Boîte de cataracte',120000);
INSERT INTO "products" VALUES(106,'Boîte de chalazion',110000);
INSERT INTO "products" VALUES(107,'Boîte de ptérygion',110000);
INSERT INTO "products" VALUES(108,'Boîte de microchirurgie',100000);
INSERT INTO "products" VALUES(109,'Valise de verres à essai',120000);
INSERT INTO "products" VALUES(110,'Test acuité visuel avec grand écran LED',350000);
INSERT INTO "products" VALUES(111,'Couteau crescent',1500);
INSERT INTO "products" VALUES(112,'Couteau Keratome',1500);
INSERT INTO "products" VALUES(113,'Visqueux',4000);
INSERT INTO "products" VALUES(114,'Implant',4000);
INSERT INTO "products" VALUES(115,'Réfractomètre',2300000);
INSERT INTO "products" VALUES(116,'Tableau AV ou Logiciel',250000);
CREATE TABLE staging_spreadsheet_products (
  id INTEGER PRIMARY KEY,
  source_id INTEGER,
  product_name TEXT,
  quantity NUMERIC,
  unit_price NUMERIC,
  total NUMERIC,
  sheet_name TEXT,
  row_number INTEGER,
  import_status TEXT DEFAULT 'pending',
  matched_product_id INTEGER,
  FOREIGN KEY (source_id) REFERENCES catalog_sources(id),
  FOREIGN KEY (matched_product_id) REFERENCES products(id)
);
CREATE VIEW v_order_details AS
SELECT
  o.id AS order_id,
  o.invoice_number,
  o.document_type,
  o.order_date,
  c.id AS client_id,
  c.name AS client_name,
  oi.line_number,
  p.id AS product_id,
  p.name AS product_name,
  oi.product_name_raw,
  oi.quantity,
  oi.unit_price,
  oi.line_total,
  o.total_amount AS order_total,
  o.source_file
FROM orders o
JOIN clients c ON c.id = o.client_id
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON p.id = oi.product_id;
CREATE VIEW v_product_price_summary AS
SELECT
  p.id AS product_id,
  p.name AS product_name,
  COUNT(pph.id) AS price_observations,
  MIN(pph.price) AS min_unit_price,
  MAX(pph.price) AS max_unit_price,
  ROUND(AVG(pph.price), 2) AS avg_unit_price,
  SUM(COALESCE(pph.quantity,0)) AS total_quantity_sold,
  SUM(COALESCE(pph.line_total,0)) AS total_revenue
FROM products p
LEFT JOIN product_price_history pph ON pph.product_id = p.id
GROUP BY p.id, p.name;
CREATE VIEW v_client_order_summary AS
SELECT
  c.id AS client_id,
  c.name AS client_name,
  COUNT(DISTINCT o.id) AS orders_count,
  COUNT(oi.id) AS order_lines_count,
  SUM(COALESCE(oi.line_total,0)) AS total_lines_amount,
  SUM(COALESCE(o.total_amount,0)) AS total_orders_amount
FROM clients c
LEFT JOIN orders o ON o.client_id = c.id
LEFT JOIN order_items oi ON oi.order_id = o.id
GROUP BY c.id, c.name;
CREATE VIEW v_order_total_control AS
SELECT
  o.id AS order_id,
  o.invoice_number,
  o.source_file,
  o.total_amount AS declared_total,
  SUM(COALESCE(oi.line_total,0)) AS computed_lines_total,
  (COALESCE(o.total_amount,0) - SUM(COALESCE(oi.line_total,0))) AS difference
FROM orders o
LEFT JOIN order_items oi ON oi.order_id = o.id
GROUP BY o.id;
CREATE INDEX idx_orders_client ON orders(client_id);
CREATE INDEX idx_orders_invoice_number ON orders(invoice_number);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_product_aliases_norm ON product_aliases(normalized_alias);
CREATE INDEX idx_client_aliases_norm ON client_aliases(normalized_alias);
CREATE INDEX idx_price_history_product ON product_price_history(product_id);
COMMIT;
PRAGMA foreign_keys=ON;
