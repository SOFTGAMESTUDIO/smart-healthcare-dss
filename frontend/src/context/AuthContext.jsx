import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import axios from 'axios'

const AuthContext = createContext(null)

const API_BASE = 'http://localhost:8000'

export function AuthProvider({ children }) {
  const [user, setUser]                   = useState(null)
  const [token, setToken]                 = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [loading, setLoading]             = useState(true) // true while restoring session

  // ── Restore session from localStorage on mount ──────────────────────────────
  useEffect(() => {
    const savedToken = localStorage.getItem('token')
    const savedUser  = localStorage.getItem('user')

    if (savedToken && savedUser) {
      try {
        const parsedUser = JSON.parse(savedUser)
        setToken(savedToken)
        setUser(parsedUser)
        setIsAuthenticated(true)
      } catch {
        // Corrupted data – wipe it
        localStorage.removeItem('token')
        localStorage.removeItem('user')
      }
    }
    setLoading(false)
  }, [])

  // ── Login ───────────────────────────────────────────────────────────────────
  /**
   * Calls POST /api/auth/login with OAuth2PasswordRequestForm (application/x-www-form-urlencoded).
   * Returns { success: true } or { success: false, error: string }.
   */
  const login = useCallback(async (username, password) => {
    try {
      const formData = new URLSearchParams()
      formData.append('username', username)
      formData.append('password', password)

      const response = await axios.post(`${API_BASE}/api/auth/login`, formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })

      const { access_token, token_type } = response.data

      // Try to fetch the current user profile after login
      let profile = { username }
      try {
        const meRes = await axios.get(`${API_BASE}/api/auth/me`, {
          headers: { Authorization: `Bearer ${access_token}` },
        })
        profile = meRes.data
      } catch {
        // /me not available – use minimal profile
      }

      localStorage.setItem('token', access_token)
      localStorage.setItem('user', JSON.stringify(profile))

      setToken(access_token)
      setUser(profile)
      setIsAuthenticated(true)

      return { success: true }
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'Login failed. Please check your credentials.'
      return { success: false, error: message }
    }
  }, [])

  // ── Logout ──────────────────────────────────────────────────────────────────
  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
    setIsAuthenticated(false)
    window.location.href = '/login'
  }, [])

  const value = {
    user,
    token,
    isAuthenticated,
    loading,
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// ── Hook ─────────────────────────────────────────────────────────────────────
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used inside an <AuthProvider>')
  }
  return ctx
}

export default AuthContext
