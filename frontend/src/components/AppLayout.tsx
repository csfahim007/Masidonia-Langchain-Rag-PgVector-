import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { authAPI } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { useThemeStore } from '../store/themeStore';

const navItems = [
  { to: '/dashboard', label: 'Overview', icon: '🏠' },
  { to: '/documents', label: 'Documents', icon: '📄' },
  { to: '/chat', label: 'AI Chat', icon: '💬' },
  { to: '/search', label: 'Search', icon: '🔍' },
  { to: '/analytics', label: 'Analytics', icon: '📊' },
];

export const AppLayout = () => {
  const { user, logout, setUser } = useAuthStore();
  const { theme, toggleTheme } = useThemeStore();
  const navigate = useNavigate();
  const [showProfile, setShowProfile] = useState(false);
  const [fullName, setFullName] = useState(user?.full_name || '');

  const displayName = user?.full_name || user?.email?.split('@')[0] || 'User';
  const initials = displayName.slice(0, 2).toUpperCase();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleSaveProfile = async () => {
    try {
      const res = await authAPI.updateProfile({ full_name: fullName });
      setUser({ ...user!, full_name: res.data.full_name });
      setShowProfile(false);
      toast.success('Profile updated');
    } catch {
      toast.error('Failed to update profile');
    }
  };

  return (
    <div className="min-h-screen dashboard-bg flex">
      {showProfile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60" onClick={() => setShowProfile(false)}>
          <div className="app-card p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold mb-4">Edit Profile</h2>
            <p className="text-sm text-muted mb-2">{user?.email}</p>
            <input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Full name"
              className="w-full px-4 py-3 rounded-xl app-input text-sm mb-4"
            />
            <div className="flex gap-3">
              <button onClick={() => setShowProfile(false)} className="flex-1 py-2 rounded-xl app-card text-sm">Cancel</button>
              <button onClick={handleSaveProfile} className="flex-1 py-2 rounded-xl bg-indigo-600 text-white text-sm font-semibold">Save</button>
            </div>
          </div>
        </div>
      )}

      <aside className="hidden md:flex w-64 flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)]">
        <div className="p-6 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <span className="text-white text-sm font-bold">M</span>
            </div>
            <div>
              <p className="font-bold text-sm">Masidonia</p>
              <p className="text-xs text-muted">Intelligent Platform</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                    : 'text-muted hover:bg-[var(--color-surface-hover)]'
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-[var(--color-border)] space-y-3">
          <button onClick={toggleTheme} className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm text-muted hover:bg-[var(--color-surface-hover)]">
            {theme === 'dark' ? '☀️ Light mode' : '🌙 Dark mode'}
          </button>
          <button onClick={() => { setFullName(user?.full_name || ''); setShowProfile(true); }} className="w-full flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-[var(--color-surface-hover)]">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-xs font-bold text-white">
              {initials}
            </div>
            <div className="flex-1 min-w-0 text-left">
              <p className="text-sm font-medium truncate">{displayName}</p>
              <p className="text-xs text-muted capitalize">{user?.role || 'user'}</p>
            </div>
          </button>
          <button onClick={handleLogout} className="w-full px-3 py-2 rounded-xl text-sm text-red-400 hover:bg-red-500/10">
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="md:hidden sticky top-0 z-40 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 flex items-center justify-between">
          <span className="font-bold">Masidonia</span>
          <button onClick={handleLogout} className="text-sm text-red-400">Sign out</button>
        </header>
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
