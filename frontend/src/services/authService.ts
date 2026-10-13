import { apiRequest, ApiError } from './apiClient';
import { User, AuthResponse, UserRole } from '../types';
import { mockStore } from '../mocks/mockStore';
import { DEMO_ACCOUNTS } from '../lib/constants';

export const authService = {
  async login(email: string, password: string): Promise<AuthResponse> {
    try {
      const res = await apiRequest<AuthResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem('nimbus_auth_token', res.access_token);
      localStorage.setItem('nimbus_user', JSON.stringify(res.user));
      mockStore.currentUser = res.user;
      return res;
    } catch (err: any) {
      // If backend offline or matching demo credentials, use mock login
      const match = DEMO_ACCOUNTS.find((a) => a.email.toLowerCase() === email.toLowerCase());
      if (match) {
        const mockUser: User = {
          id: `usr-${match.role}`,
          email: match.email,
          full_name: match.name,
          role: match.role as UserRole,
          organization_id: match.role === 'partner' ? 'org-001' : 'org-001',
          is_active: true,
          created_at: '2026-10-01T08:00:00Z',
        };
        const token = `demo-token-${match.role}-${Date.now()}`;
        localStorage.setItem('nimbus_auth_token', token);
        localStorage.setItem('nimbus_user', JSON.stringify(mockUser));
        mockStore.currentUser = mockUser;
        return {
          access_token: token,
          token_type: 'bearer',
          user: mockUser,
        };
      }
      throw new ApiError('Invalid email or password. Please use registered demo credentials.', 'AUTH_FAILED', 401);
    }
  },

  async getCurrentUser(): Promise<User> {
    try {
      const res = await apiRequest<User>('/auth/me');
      localStorage.setItem('nimbus_user', JSON.stringify(res));
      mockStore.currentUser = res;
      return res;
    } catch {
      const stored = localStorage.getItem('nimbus_user');
      if (stored) {
        try {
          const u = JSON.parse(stored);
          mockStore.currentUser = u;
          return u;
        } catch {
          // fallback
        }
      }
      return mockStore.currentUser;
    }
  },

  async switchRole(role: UserRole): Promise<User> {
    const account = DEMO_ACCOUNTS.find((a) => a.role === role) || DEMO_ACCOUNTS[1];
    const newUser: User = {
      id: `usr-${role}`,
      email: account.email,
      full_name: account.name,
      role: role,
      organization_id: 'org-001',
      is_active: true,
      created_at: '2026-10-01T08:00:00Z',
    };
    localStorage.setItem('nimbus_user', JSON.stringify(newUser));
    localStorage.setItem('nimbus_auth_token', `demo-token-${role}`);
    mockStore.currentUser = newUser;
    return newUser;
  },

  logout(): void {
    localStorage.removeItem('nimbus_auth_token');
    localStorage.removeItem('nimbus_user');
  },
};
