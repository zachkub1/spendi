/**
 * Authentication types shared between frontend and backend.
 * Corresponds to Pydantic models in backend/app/auth/routes.py
 */

export interface User {
  id: string;
  email: string;
  display_name: string | null;
  oauth_provider: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface AuthError {
  message: string;
  code?: string;
}
