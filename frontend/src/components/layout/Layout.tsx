import { ReactNode } from 'react';
import Navbar from './Navbar';
import Sidebar from './Sidebar';
import Toast from '@/components/common/Toast';
import { useUIStore } from '@/store';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const { sidebarOpen } = useUIStore();

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="flex">
        <Sidebar />
        <main
          className={`flex-1 p-6 transition-all duration-200 ${
            sidebarOpen ? 'ml-64' : 'ml-16'
          }`}
        >
          {children}
        </main>
      </div>
      <Toast />
    </div>
  );
}
