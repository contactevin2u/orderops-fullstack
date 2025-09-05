import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { User, getStoredUser, isAuthenticated, login as authLogin, logout as authLogout } from '@/lib/auth';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const storedUser = getStoredUser();
    setUser(storedUser);
    setLoading(false);
  }, []);

  const login = async (username: string, password: string) => {
    const result = await authLogin(username, password);
    if (result.success) {
      const newUser = getStoredUser();
      setUser(newUser);
    }
    return result;
  };

  const logout = () => {
    authLogout();
    setUser(null);
  };

  return {
    user,
    loading,
    isAuthenticated: isAuthenticated(),
    login,
    logout,
  };
}

export function useRequireAuth() {
  const { user, loading, isAuthenticated } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [loading, isAuthenticated, router]);

  return { user, loading, isAuthenticated };
}