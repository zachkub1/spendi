/**
 * Token storage utilities for managing JWT tokens in localStorage.
 * Provides functions to get, set, clear, and validate tokens.
 */

const TOKEN_KEY = 'ledgerly_auth_token';

/**
 * Get the JWT token from localStorage.
 */
export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Set the JWT token in localStorage.
 */
export function setToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
}

/**
 * Clear the JWT token from localStorage.
 */
export function clearToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * Check if a JWT token is expired.
 * Returns true if token is expired or invalid.
 */
export function isTokenExpired(token: string): boolean {
  try {
    // JWT structure: header.payload.signature
    const parts = token.split('.');
    if (parts.length !== 3) return true;

    // Decode payload (base64url)
    const payload = JSON.parse(atob(parts[1]));

    if (!payload.exp) return true;

    // exp is in seconds, Date.now() is in milliseconds
    const expirationTime = payload.exp * 1000;
    const currentTime = Date.now();

    return currentTime >= expirationTime;
  } catch (error) {
    // If parsing fails, consider token invalid
    return true;
  }
}
