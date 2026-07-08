import { useAuthStore } from '../store/authStore';
import { Navigate, Outlet } from 'react-router-dom';

const Spinner = () => (
  <div className="min-h-screen auth-grid-bg flex items-center justify-center">
    <div className="text-center">
      <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-indigo-500/30">
        <svg className="animate-spin w-6 h-6 text-white" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>
      <p className="text-slate-400 text-sm">Loading...</p>
    </div>
  </div>
);

export const GuestRoute = () => {
  const { isAuthenticated, isLoading } = useAuthStore();

  if (isLoading) return <Spinner />;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return <Outlet />;
};
