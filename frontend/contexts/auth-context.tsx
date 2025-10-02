"use client"

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react"
import { AuthService } from "@/services/auth-service"
import { useRouter } from "next/navigation"

// Update the User interface to match what we can extract from the JWT token
interface User {
  id: number
  username: string
  email: string
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  // Refresh token function
  const refreshToken = useCallback(async () => {
    try {
      const refreshTokenValue = localStorage.getItem("refreshToken")
      if (!refreshTokenValue) {
        return
      }

      const { access } = await AuthService.refreshToken(refreshTokenValue)
      localStorage.setItem("accessToken", access)

      // Update user data with new token
      const userData = await AuthService.getUserProfile(access)
      setUser(userData)
    } catch (error) {
      console.error("Error refreshing token:", error)
      // If refresh fails, log out
      logout()
    }
  }, [])

  // Logout function
  const logout = useCallback(() => {
    localStorage.removeItem("accessToken")
    localStorage.removeItem("refreshToken")
    setUser(null)
    router.push("/auth")
  }, [router])

  useEffect(() => {
    // Check if user is already logged in
    const checkAuth = async () => {
      const accessToken = localStorage.getItem("accessToken")
      const refreshTokenValue = localStorage.getItem("refreshToken")

      if (!accessToken || !refreshTokenValue) {
        setIsLoading(false)
        return
      }

      try {
        // Try to get user profile with current access token
        const userData = await AuthService.getUserProfile(accessToken)
        setUser(userData)
      } catch (error) {
        // If access token is expired, try to refresh it
        try {
          await refreshToken()
        } catch (refreshError) {
          // If refresh fails, log out
          logout()
        }
      } finally {
        setIsLoading(false)
      }
    }

    checkAuth()

    // Set up token refresh interval - refresh every 10 minutes
    const refreshInterval = setInterval(refreshToken, 10 * 60 * 1000)

    return () => clearInterval(refreshInterval)
  }, [logout, refreshToken])

  // Update the login function
  const login = async (username: string, password: string) => {
    setIsLoading(true)
    try {
      const response = await AuthService.login({ username, password })
      localStorage.setItem("accessToken", response.access)
      localStorage.setItem("refreshToken", response.refresh)

      // Extract user info from JWT token
      const userData = await AuthService.getUserProfile(response.access)
      setUser(userData)

      // Initialize user data in MongoDB if needed
      try {
        // Call API route to initialize user data instead of direct MongoDB access
        const accessToken = response.access
        await fetch("/api/user/initialize", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({
            userId: userData.id.toString(),
            username: userData.username,
            email: userData.email,
          }),
        })
      } catch (initError) {
        console.error("Error initializing user data:", initError)
        // Continue login process even if initialization fails
      }

      router.push("/dashboard")
    } catch (error) {
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  // Update the register function
  const register = async (username: string, email: string, password: string) => {
    setIsLoading(true)
    try {
      const response = await AuthService.register({ username, email, password })
      localStorage.setItem("accessToken", response.access)
      localStorage.setItem("refreshToken", response.refresh)

      // Extract user info from JWT token
      const userData = await AuthService.getUserProfile(response.access)
      setUser(userData)

      // Initialize user data in MongoDB
      try {
        // Call API route to initialize user data instead of direct MongoDB access
        const accessToken = response.access
        await fetch("/api/user/initialize", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({
            userId: userData.id.toString(),
            username: userData.username,
            email: userData.email,
          }),
        })
      } catch (initError) {
        console.error("Error initializing user data:", initError)
        // Continue registration process even if initialization fails
      }

      router.push("/dashboard")
    } catch (error) {
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        refreshToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
