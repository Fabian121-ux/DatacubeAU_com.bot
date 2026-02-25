import type { LucideIcon } from 'lucide-react';
import {
  LayoutDashboard,
  SlidersHorizontal,
  TerminalSquare,
  BookOpenCheck,
  ScrollText,
  Users,
  TrendingUp,
  Smartphone
} from 'lucide-react';

export interface AdminNavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const ADMIN_NAV_ITEMS: AdminNavItem[] = [
  { href: '/admin', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/admin/settings', label: 'Settings', icon: SlidersHorizontal },
  { href: '/admin/commands', label: 'Commands', icon: TerminalSquare },
  { href: '/admin/numbers', label: 'Numbers', icon: Smartphone },
  { href: '/admin/training', label: 'Training', icon: BookOpenCheck },
  { href: '/admin/logs', label: 'Logs', icon: ScrollText },
  { href: '/admin/users', label: 'Users', icon: Users },
  { href: '/admin/trends', label: 'Trends', icon: TrendingUp }
];
