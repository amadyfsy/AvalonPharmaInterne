from datetime import datetime

from ..extensions import db

MOTIFS_SORTIE = (
    ('demission', 'Démission'),
    ('fin_contrat', 'Fin de contrat'),
    ('licenciement', 'Licenciement'),
    ('rupture_conventionnelle', 'Rupture conventionnelle'),
    ('retraite', 'Départ à la retraite'),
    ('autre', 'Autre'),
)


class Employe(db.Model):
    __tablename__ = 'employes'
    id = db.Column(db.Integer, primary_key=True)
    matricule = db.Column(db.String(50), unique=True, nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    date_naissance = db.Column(db.Date, nullable=False)
    cin = db.Column(db.String(50), unique=True, nullable=False) # Will store encrypted
    telephone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    adresse = db.Column(db.Text, nullable=True)
    poste = db.Column(db.String(100), nullable=False)
    departement = db.Column(db.String(100), nullable=False)
    date_embauche = db.Column(db.Date, nullable=False)
    type_contrat = db.Column(db.Enum('CDI', 'CDD', 'Stage', name='type_contrats'), nullable=False)
    # Obligatoire pour CDD/Stage (contrôlé côté formulaire)
    date_fin_contrat = db.Column(db.Date, nullable=True)
    salaire_base = db.Column(db.Numeric(10, 2), nullable=False)
    # Taux en % (ex. 5.6 = 5,6 %) — utilisés pour le calcul des bulletins
    taux_ipres_salarial = db.Column(db.Numeric(6, 3), nullable=False, default=5.6)
    taux_css_salarial = db.Column(db.Numeric(6, 3), nullable=False, default=7.0)
    taux_ipres_patronal = db.Column(db.Numeric(6, 3), nullable=False, default=8.4)
    taux_css_patronal = db.Column(db.Numeric(6, 3), nullable=False, default=14.0)
    seuil_irpp = db.Column(db.Numeric(12, 2), nullable=False, default=30000)
    taux_irpp = db.Column(db.Numeric(6, 3), nullable=False, default=10.0)
    rib_bancaire = db.Column(db.String(255), nullable=True) # Encrypted
    document_cin = db.Column(db.String(255), nullable=True)
    document_contrat = db.Column(db.String(255), nullable=True)
    statut = db.Column(db.Enum('actif', 'inactif', 'suspendu', name='statut_employe'), default='actif')
    date_sortie = db.Column(db.Date, nullable=True)
    motif_sortie = db.Column(db.String(40), nullable=True)
    notes_sortie = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relations
    conges = db.relationship('Conge', backref='employe', lazy=True)
    paies = db.relationship('Paie', backref='employe', lazy=True)

    @property
    def motif_sortie_label(self) -> str:
        return dict(MOTIFS_SORTIE).get(self.motif_sortie or '', self.motif_sortie or '—')

    def parametres_paie(self) -> dict[str, float]:
        """Taux et seuils pour le calcul bulletin (pourcentages, ex. 5.6 = 5,6 %)."""
        return {
            'taux_ipres_salarial': float(self.taux_ipres_salarial if self.taux_ipres_salarial is not None else 5.6),
            'taux_css_salarial': float(self.taux_css_salarial if self.taux_css_salarial is not None else 7.0),
            'taux_ipres_patronal': float(self.taux_ipres_patronal if self.taux_ipres_patronal is not None else 8.4),
            'taux_css_patronal': float(self.taux_css_patronal if self.taux_css_patronal is not None else 14.0),
            'seuil_irpp': float(self.seuil_irpp if self.seuil_irpp is not None else 30000),
            'taux_irpp': float(self.taux_irpp if self.taux_irpp is not None else 10.0),
        }


class Conge(db.Model):
    __tablename__ = 'conges'
    id = db.Column(db.Integer, primary_key=True)
    employe_id = db.Column(db.Integer, db.ForeignKey('employes.id'), nullable=False)
    type_conge = db.Column(db.Enum('annuel', 'maladie', 'maternite', 'sans_solde', name='type_conges'), nullable=False)
    date_debut = db.Column(db.Date, nullable=False)
    date_fin = db.Column(db.Date, nullable=False)
    nb_jours = db.Column(db.Float, nullable=False)
    motif = db.Column(db.Text, nullable=True)
    statut = db.Column(db.Enum('en_attente', 'approuve', 'refuse', name='statut_conge'), default='en_attente')
    approuve_par = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Paie(db.Model):
    __tablename__ = 'paies'
    id = db.Column(db.Integer, primary_key=True)
    employe_id = db.Column(db.Integer, db.ForeignKey('employes.id'), nullable=False)
    mois = db.Column(db.Integer, nullable=False)
    annee = db.Column(db.Integer, nullable=False)
    salaire_base = db.Column(db.Numeric(10, 2), nullable=False)
    primes = db.Column(db.Numeric(10, 2), default=0.00)
    heures_sup = db.Column(db.Numeric(10, 2), default=0.00)
    deductions = db.Column(db.Numeric(10, 2), default=0.00)
    montant_brut = db.Column(db.Numeric(10, 2), nullable=True)
    ipres_salarial = db.Column(db.Numeric(10, 2), default=0.00)
    css_salarial = db.Column(db.Numeric(10, 2), default=0.00)
    cotisations_sociales = db.Column(db.Numeric(10, 2), default=0.00)
    ipres_patronal = db.Column(db.Numeric(10, 2), default=0.00)
    css_patronal = db.Column(db.Numeric(10, 2), default=0.00)
    charges_patronales = db.Column(db.Numeric(10, 2), default=0.00)
    irpp = db.Column(db.Numeric(10, 2), default=0.00)
    net_a_payer = db.Column(db.Numeric(10, 2), nullable=False)
    date_paiement = db.Column(db.Date, nullable=True)
    mode_paiement = db.Column(db.String(50), nullable=True)
    depense_id = db.Column(db.Integer, db.ForeignKey('depenses.id'), nullable=True, index=True)
    statut = db.Column(db.Enum('genere', 'paye', name='statut_paie'), default='genere')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    depense = db.relationship('Depense', foreign_keys=[depense_id])

    @property
    def brut(self) -> float:
        if self.montant_brut is not None:
            return float(self.montant_brut)
        return float(self.salaire_base or 0) + float(self.primes or 0) + float(self.heures_sup or 0)

    @property
    def ipres_salarial_calc(self) -> float:
        if self.ipres_salarial is not None and float(self.ipres_salarial) > 0:
            return float(self.ipres_salarial)
        return round(self.brut * 0.056, 2)

    @property
    def css_salarial_calc(self) -> float:
        if self.css_salarial is not None and float(self.css_salarial) > 0:
            return float(self.css_salarial)
        cot = float(self.cotisations_sociales or 0)
        if cot > 0:
            return round(max(cot - self.ipres_salarial_calc, 0), 2)
        return round(self.brut * 0.07, 2)

    @property
    def ipres_patronal_calc(self) -> float:
        if self.ipres_patronal is not None and float(self.ipres_patronal) > 0:
            return float(self.ipres_patronal)
        return round(self.brut * 0.084, 2)

    @property
    def css_patronal_calc(self) -> float:
        if self.css_patronal is not None and float(self.css_patronal) > 0:
            return float(self.css_patronal)
        ch = float(self.charges_patronales or 0)
        if ch > 0:
            return round(max(ch - self.ipres_patronal_calc, 0), 2)
        return round(self.brut * 0.14, 2)

    @property
    def cotisations_sociales_calc(self) -> float:
        if self.cotisations_sociales is not None and float(self.cotisations_sociales) > 0:
            return float(self.cotisations_sociales)
        return round(self.ipres_salarial_calc + self.css_salarial_calc, 2)

    @property
    def charges_patronales_calc(self) -> float:
        if self.charges_patronales is not None and float(self.charges_patronales) > 0:
            return float(self.charges_patronales)
        return round(self.ipres_patronal_calc + self.css_patronal_calc, 2)

    @property
    def cout_total_employeur(self) -> float:
        return round(self.brut + self.charges_patronales_calc, 2)

    @property
    def total_retenues_salariales(self) -> float:
        return (
            self.cotisations_sociales_calc
            + float(self.irpp or 0)
            + float(self.deductions or 0)
        )
