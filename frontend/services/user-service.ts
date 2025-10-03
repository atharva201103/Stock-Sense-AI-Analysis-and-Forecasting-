// User service for handling user-specific API calls

const API_URL = "http://127.0.0.1:8000/api" // Use Django backend API URL

async function getErrorMessage(response: Response, fallback: string) {
  try {
    const data = await response.json()
    return data.error || fallback
  } catch {
    try {
      const text = await response.text()
      return text || fallback
    } catch {
      return fallback
    }
  }
}

export const UserService = {
  // Get user portfolio
  getUserPortfolio: async (token: string): Promise<any> => {
    const response = await fetch(`${API_URL}/user/portfolio/`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      const errorMessage = await getErrorMessage(response, "Failed to fetch portfolio data")
      throw new Error(errorMessage)
    }

    return response.json()
  },

  // Get user watchlist
  getUserWatchlist: async (token: string): Promise<any> => {
    try {
      const response = await fetch(`${API_URL}/user/watchlist/`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        const errorMessage = await getErrorMessage(response, "Failed to fetch watchlist data")
        throw new Error(errorMessage)
      }

      return response.json()
    } catch (error) {
      console.error("Watchlist fetch error:", error)
      throw error
    }
  },

  // Get user balance
  getUserBalance: async (token: string): Promise<any> => {
    try {
      const response = await fetch(`${API_URL}/user/balance/`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        const errorMessage = await getErrorMessage(response, "Failed to fetch balance data")
        throw new Error(errorMessage)
      }

      return response.json()
    } catch (error) {
      console.error("Balance fetch error:", error)
      throw error
    }
  },

  // Update user balance
  updateUserBalance: async (token: string, balance: number): Promise<any> => {
    try {
      const response = await fetch(`${API_URL}/user/balance/`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ balance }),
      })

      if (!response.ok) {
        const errorMessage = await getErrorMessage(response, "Failed to update balance")
        throw new Error(errorMessage)
      }

      return response.json()
    } catch (error) {
      console.error("Balance update error:", error)
      throw error
    }
  },

  // Add stock to watchlist
  addToWatchlist: async (token: string, symbol: string, name: string): Promise<any> => {
    try {
      const response = await fetch(`${API_URL}/user/watchlist/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ stock_symbol: symbol, stock_name: name }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        // Return the error response instead of throwing for "already in watchlist" case
        return errorData
      }

      return response.json()
    } catch (error) {
      console.error("Add to watchlist error:", error)
      throw error
    }
  },

  // Remove stock from watchlist - This endpoint needs to be implemented in backend if required
  removeFromWatchlist: async (token: string, symbol: string): Promise<any> => {
    // Placeholder: Backend endpoint for removing stock from watchlist not implemented yet
    throw new Error("Remove from watchlist not implemented in backend")
  },

  // Execute trade - This endpoint needs to be implemented in backend if required
  executeTrade: async (
    token: string,
    symbol: string,
    action: "buy" | "sell",
    shares: number,
    price: number,
  ): Promise<any> => {
    // Placeholder: Backend endpoint for executing trade not implemented yet
    throw new Error("Execute trade not implemented in backend")
  },
}
