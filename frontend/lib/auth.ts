// Authentication utilities and route guards

import { useRouter } from 'next/router';
import { useEffect } from 'react';

export type UserRole = 'ADMIN' | 'CASHIER' | 'DRIVER';

export interface User {
  id: string;
  username: string;
  role: UserRole;
  email?: string;
}

/**
 * Get stored auth token
 */
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('authToken');
}

/**
 * Set auth token
 */
export function setAuthToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('authToken', token);
}

/**
 * Remove auth token
 */
export function removeAuthToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('authToken');
  localStorage.removeItem('user');
}

/**
 * Get stored user info
 */
export function getStoredUser(): User | null {
  if (typeof window === 'undefined') return null;
  const stored = localStorage.getItem('user');
  try {
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

/**
 * Set user info
 */
export function setStoredUser(user: User): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('user', JSON.stringify(user));
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return !!getAuthToken();
}

/**
 * Check if user has required role
 */
export function hasRole(user: User | null, requiredRole: UserRole): boolean {
  if (!user) return false;
  
  // Admin can access everything
  if (user.role === 'ADMIN') return true;
  
  // Exact role match
  return user.role === requiredRole;
}

/**
 * Check if user has any of the required roles
 */
export function hasAnyRole(user: User | null, requiredRoles: UserRole[]): boolean {
  if (!user) return false;
  return requiredRoles.some(role => hasRole(user, role));
}

/**
 * Hook to redirect unauthenticated users
 */
export function useRequireAuth(redirectTo: string = '/login') {
  const router = useRouter();
  
  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace(redirectTo);
    }
  }, [router, redirectTo]);
  
  return isAuthenticated();
}

/**
 * Hook to require specific role
 */
export function useRequireRole(requiredRole: UserRole, redirectTo: string = '/unauthorized') {
  const router = useRouter();
  const user = getStoredUser();
  
  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/login');
      return;
    }
    
    if (!hasRole(user, requiredRole)) {
      router.replace(redirectTo);
    }
  }, [router, requiredRole, redirectTo, user]);
  
  return hasRole(user, requiredRole);
}

/**
 * Logout user and redirect
 */
export function logout(redirectTo: string = '/login') {
  removeAuthToken();
  
  if (typeof window !== 'undefined') {
    window.location.href = redirectTo;
  }
}

/**
 * Login with credentials
 */
export async function login(username: string, password: string): Promise<{ success: boolean; error?: string }> {
  try {
    // This would typically call your login API
    const response = await fetch('/_api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    
    if (!response.ok) {
      const error = await response.text();
      return { success: false, error };
    }
    
    const data = await response.json();
    
    if (data.token && data.user) {
      setAuthToken(data.token);
      setStoredUser(data.user);
      return { success: true };
    }
    
    return { success: false, error: 'Invalid response from server' };
  } catch (error) {
    return { success: false, error: 'Network error. Please try again.' };
  }
}