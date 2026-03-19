/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useEffect, useState } from 'react'
import type { AuthContextType, LoginForm } from '../types/auth.types'
import type { User } from '../types/user.types'
// import type { Tenant } from '../types/tenant.types'

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // MOCK USER for Dev environment where Auth/Tenants are disabled in DB
  // This is critical because the backend no longer has the 'tenants' table,
  // but the frontend requires a user to function.
  const MOCK_USER: User = {
    id: 'dev-admin-user',
    email: 'admin@cortex.com',
    first_name: 'Dev',
    last_name: 'Admin',
    role: 'admin',
  }

  const [user, setUser] = useState<User | null>(MOCK_USER)
  const [isLoading] = useState(false)

  // Mock functions
  const login = async (credentials: LoginForm) => {
    console.log('Mock login with', credentials)
    setUser(MOCK_USER)
  }

  const logout = async () => {
    console.log('Mock logout')
  }

  useEffect(() => {
    console.log('AuthProvider initialized with MOCK USER')
  }, [])

  const value: AuthContextType = {
    user,
    isLoading,
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
