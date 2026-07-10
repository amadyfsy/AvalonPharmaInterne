import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  Ambulance,
  Baby,
  BadgeCheck,
  Bone,
  Clock,
  Ear,
  Eye,
  Globe,
  GraduationCap,
  Heart,
  Microscope,
  Pill,
  ScanLine,
  Scissors,
  Smile,
  Stethoscope,
  Truck,
} from 'lucide-react';

export interface SpecialiteIconDef {
  name: string;
  icon: LucideIcon;
}

export const SPECIALITE_ICONS: SpecialiteIconDef[] = [
  { name: 'Ophtalmologie', icon: Eye },
  { name: 'Gynécologie', icon: Baby },
  { name: 'Cardiologie', icon: Heart },
  { name: 'Dentaire', icon: Smile },
  { name: 'Orthopédie', icon: Bone },
  { name: 'Imagerie', icon: ScanLine },
  { name: 'Bloc opératoire', icon: Scissors },
  { name: 'Laboratoire', icon: Microscope },
  { name: 'Urgences', icon: Ambulance },
  { name: 'ORL', icon: Ear },
];

export const PILLAR_ICON_MAP: Record<string, LucideIcon> = {
  'Médicaments & solutions': Pill,
  'Dispositifs médicaux': Stethoscope,
  'Équipement biomédical': Activity,
  'Accompagnement expert': Truck,
};

export const VALUE_ICON_MAP: Record<string, LucideIcon> = {
  'Qualité certifiée': BadgeCheck,
  Réactivité: Clock,
  'Expertise médicale': GraduationCap,
  'Couverture nationale': Globe,
};
