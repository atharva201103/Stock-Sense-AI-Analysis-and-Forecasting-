// User service for handling user-specific API calls

const API_URL = "/api" // Use relative URL for API routes

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
    const response = await fetch(`${API_URL}/user/portfolio`, {
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
      const response = await fetch(`${API_URL}/user/watchlist`, {
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

  // Get user transactions
  getUserTransactions: async (token: string): Promise<any> => {
    try {
      const response = await fetch(`${API_URL}/user/transactions`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        const errorMessage = await getErrorMessage(response, "Failed to fetch transaction data")
        throw new Error(errorMessage)
      }

      return response.json()
    } catch (error) {
      console.error("Transactions fetch error:", error)
      throw error
    }
  },

  // Add stock to watchlist
  addToWatchlist: async (token: string, symbol: string, name: string): Promise<any> => {
    try {
      const response = await fetch(`${API_URL}/user/watchlist/add`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ symbol, name }),
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

  // Remove stock from watchlist
  removeFromWatchlist: async (token: string, symbol: string): Promise<any> => {
    try {
      const response = await fetch(`${API_URL}/user/watchlist/remove`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ symbol }),
      })

      if (!response.ok) {
        const errorMessage = await getErrorMessage(response, "Failed to remove stock from watchlist")
        throw new Error(errorMessage)
      }

      return response.json()
    } catch (error) {
      console.error("Remove from watchlist error:", error)
      throw error
    }
  },

  // Execute trade
  executeTrade: async (
    token: string,
    symbol: string,
    action: "buy" | "sell",
    shares: number,
    price: number,
  ): Promise<any> => {
    try {
      const response = await fetch(`${API_URL}/user/trade`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ symbol, action, shares, price }),
      })

      if (!response.ok) {
        const errorMessage = await getErrorMessage(response, "Failed to execute trade")
        throw new Error(errorMessage)
      }

      return response.json()
    } catch (error) {
      console.error("Execute trade error:", error)
      throw error
    }
  },
}
