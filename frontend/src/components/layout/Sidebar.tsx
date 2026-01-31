import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Server,
  DollarSign,
  Lightbulb,
  FileText,
  Settings,
} from 'lucide-react';
import { useUIStore } from '@/store';
import clsx from 'clsx';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Inventory', href: '/inventory', icon: Server },
  { name: 'Costs', href: '/costs', icon: DollarSign },
  { name: 'Recommendations', href: '/recommendations', icon: Lightbulb },
  { name: 'Audit Log', href: '/audit', icon: FileText },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Sidebar() {
  const { sidebarOpen } = useUIStore();

  return (
    <aside
      className={clsx(
        'fixed left-0 top-16 bottom-0 z-40 bg-white border-r border-gray-200 transition-all duration-200',
        sidebarOpen ? 'w-64' : 'w-16'
      )}
    >
      <nav className="flex flex-col gap-1 p-3">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-700 hover:bg-gray-100'
              )
            }
          >
            <item.icon className="h-5 w-5 flex-shrink-0" />
            {sidebarOpen && <span>{item.name}</span>}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
