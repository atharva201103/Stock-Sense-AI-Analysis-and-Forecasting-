// Authentication service for handling API calls

interface RegisterData {
  username: string
  email: string
  password: string
}

interface LoginData {
  username: string
  password: string
}

interface AuthResponse {
  access: string
  refresh: string
}

const API_URL = "http://127.0.0.1:8000"

export const AuthService = {
  // Register a new user
  register: async (data: RegisterData): Promise<AuthResponse> => {
    const response = await fetch(`${API_URL}/api/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || "Registration failed")
    }

    return response.json()
  },

  // Login user
  login: async (data: LoginData): Promise<AuthResponse> => {
    const response = await fetch(`${API_URL}/api/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || "Login failed")
    }

    return response.json()
  },

  // Refresh token
  refreshToken: async (refreshToken: string): Promise<{ access: string }> => {
    const response = await fetch(`${API_URL}/api/token/refresh/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ refresh: refreshToken }),
    })

    if (!response.ok) {
      throw new Error("Token refresh failed")
    }

    return response.json()
  },

  // Get user profile with token
  getUserProfile: async (token: string): Promise<any> => {
    try {
      // Decode the JWT token to extract user information
      const base64Url = token.split(".")[1]
      const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/")
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split("")
          .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
          .join(""),
      )

      const payload = JSON.parse(jsonPayload)

      // Extract user information from the payload
      const email = payload.email || ""
      let username = payload.username || ""

      // If no username is provided, generate one from email
      if (!username && email) {
        // Use the part before @ in email as username
        username = email.split("@")[0]
      }

      return {
        id: payload.user_id || payload.sub,
        username: username,
        email: email || "",
      }
    } catch (error) {
      console.error("Error decoding token:", error)
      throw new Error("Failed to decode user profile from token")
    }
  },
}
