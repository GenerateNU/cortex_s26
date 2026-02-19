import type { User } from './user.types'

export interface LoginForm {
  email: string
  password: string
}

export interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (credentials: LoginForm) => Promise<void>
  logout: () => Promise<void>
}
