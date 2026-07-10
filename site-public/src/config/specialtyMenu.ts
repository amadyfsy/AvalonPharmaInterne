import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  Ambulance,
  Baby,
  Bone,
  Brain,
  Dna,
  Droplets,
  Ear,
  Eye,
  FlaskConical,
  Heart,
  HeartPulse,
  Microscope,
  Pill,
  ScanLine,
  Scissors,
  Shield,
  Smile,
  Sparkles,
  Stethoscope,
  Syringe,
  Wind,
} from 'lucide-react';

export interface SpecialtyMenuItem {
  name: string;
  icon: LucideIcon;
}

export interface SpecialtyMenuGroup {
  title: string;
  subtitle: string;
  icon: LucideIcon;
  items: SpecialtyMenuItem[];
}

/** Icône par spécialité — aligné sur le référentiel ERP. */
const SPECIALTY_ICON_MAP: Record<string, LucideIcon> = {
  Ophtalmologie: Eye,
  Oncologie: Dna,
  Cardiologie: Heart,
  'Médecine interne': Stethoscope,
  Pédiatrie: Baby,
  Gynécologie: Baby,
  Neurologie: Brain,
  Dermatologie: Sparkles,
  ORL: Ear,
  'Gastro-entérologie': Activity,
  Pneumologie: Wind,
  Rhumatologie: Bone,
  Endocrinologie: Droplets,
  Néphrologie: Droplets,
  Urologie: Syringe,
  Infectiologie: Shield,
  Dentaire: Smile,
  'Dentaire (Fauteuils)': Smile,
  Orthopédie: Bone,
  'Chirurgie générale': Scissors,
  'Bloc opératoire': Scissors,
  Stérilisation: Sparkles,
  Imagerie: ScanLine,
  Laboratoire: Microscope,
  Urgences: Ambulance,
  Réanimation: HeartPulse,
  Néonatologie: Baby,
  Autre: FlaskConical,
};

export function specialtyIcon(name: string): LucideIcon {
  return SPECIALTY_ICON_MAP[name] ?? Stethoscope;
}

function items(names: string[]): SpecialtyMenuItem[] {
  return names.map((name) => ({ name, icon: specialtyIcon(name) }));
}

export const SPECIALTY_MENU_GROUPS: SpecialtyMenuGroup[] = [
  {
    title: 'Médicaments & solutions',
    subtitle: 'Spécialités pharmaceutiques hospitalières et ambulatoires',
    icon: Pill,
    items: items([
      'Ophtalmologie',
      'Oncologie',
      'Cardiologie',
      'Gynécologie',
      'Médecine interne',
      'Pédiatrie',
      'Neurologie',
      'Dermatologie',
      'ORL',
      'Gastro-entérologie',
      'Pneumologie',
      'Rhumatologie',
      'Endocrinologie',
      'Néphrologie',
      'Urologie',
      'Infectiologie',
    ]),
  },
  {
    title: 'Dispositifs médicaux',
    subtitle: 'Consommables, implants et instrumentation chirurgicale',
    icon: Syringe,
    items: items([
      'Dentaire',
      'Orthopédie',
      'Ophtalmologie',
      'Chirurgie générale',
      'Cardiologie',
      'Bloc opératoire',
      'Stérilisation',
      'ORL',
    ]),
  },
  {
    title: 'Équipement biomédical',
    subtitle: 'Matériel lourd, imagerie et équipements de service',
    icon: Microscope,
    items: items([
      'Imagerie',
      'Dentaire (Fauteuils)',
      'Bloc opératoire',
      'Laboratoire',
      'Urgences',
      'Réanimation',
      'Néonatologie',
      'Stérilisation',
    ]),
  },
];

/** Spécialités mises en avant dans le sous-menu */
export const FEATURED_SPECIALTIES: SpecialtyMenuItem[] = items([
  'Ophtalmologie',
  'Gynécologie',
  'Cardiologie',
  'Bloc opératoire',
  'Laboratoire',
  'Urgences',
]);

export function specialtyCatalogUrl(name: string): string {
  return `/catalogue?specialite=${encodeURIComponent(name)}`;
}
