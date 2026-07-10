import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  Bone,
  Droplets,
  Package,
  Pill,
} from 'lucide-react';

export interface CatalogCategoryDef {
  nom: string;
  description: string;
  longDescription: string;
  examples: string[];
  icon: LucideIcon;
  searchHint: string;
}

export const CATALOG_CATEGORY_DEFS: CatalogCategoryDef[] = [
  {
    nom: 'Médicament',
    description: 'Spécialités pharmaceutiques et solutions thérapeutiques',
    longDescription:
      'Médicaments hospitaliers, spécialités et solutions pour les services cliniques.',
    examples: ['Injectables', 'Comprimés', 'Sirops', 'Ophtalmologie'],
    icon: Pill,
    searchHint: 'médicament',
  },
  {
    nom: 'Consommable',
    description: 'Dispositifs à usage unique et consommables médicaux',
    longDescription:
      'Gants, compresses, cathéters et consommables pour la pratique quotidienne.',
    examples: ['Chirurgie', 'Soins', 'Perfusion', 'Stérilisation'],
    icon: Droplets,
    searchHint: 'consommable',
  },
  {
    nom: 'Implant',
    description: 'Prothèses, implants et dispositifs implantables',
    longDescription:
      'Solutions implantables pour l’orthopédie, la chirurgie et les spécialités.',
    examples: ['Orthopédie', 'Chirurgie', 'Ophtalmologie', 'Cardiologie'],
    icon: Bone,
    searchHint: 'implant',
  },
  {
    nom: 'Équipement',
    description: 'Matériel biomédical et équipements hospitaliers',
    longDescription:
      'Imagerie, laboratoire, bloc opératoire et matériel lourd de diagnostic.',
    examples: ['Imagerie', 'Laboratoire', 'Bloc opératoire', 'Urgences'],
    icon: Activity,
    searchHint: 'équipement',
  },
];

export const CATALOG_QUICK_LINKS = [
  { label: 'Tout le catalogue', to: '/catalogue' },
  { label: 'Ophtalmologie', to: '/catalogue?specialite=Ophtalmologie' },
  { label: 'Gynécologie', to: '/catalogue?specialite=Gynécologie' },
  { label: 'Cardiologie', to: '/catalogue?specialite=Cardiologie' },
  { label: 'Bloc opératoire', to: '/catalogue?specialite=Bloc opératoire' },
  { label: 'Laboratoire', to: '/catalogue?specialite=Laboratoire' },
] as const;

export const CATALOG_MENU_ICON = Package;
