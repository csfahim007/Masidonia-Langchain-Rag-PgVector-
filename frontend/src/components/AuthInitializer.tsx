import { useEffect, type ReactNode } from 'react';
import { useAuthStore } from '../store/authStore';

export const AuthInitializer = ({ children }: { children: ReactNode }) => {
  const loadUser = useAuthStore((state) => state.loadUser);

  useEffect(() => {
    void loadUser();
  }, [loadUser]);

  return <>{children}</>;
};
