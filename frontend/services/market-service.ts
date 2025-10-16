const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3000"

export interface MarketData {
  symbol: string
  name: string
  currentPrice: number
  change: number
  changePercent: number
  open?: number
  high?: number
  low?: number
  volume?: number
  lastUpdated: string
  note?: string
}

export const MarketService = {
  // Get real-time market data for a symbol
  getMarketData: async (symbol: string): Promise<MarketData> => {
    const response = await fetch(`${API_URL}/api/market?symbol=${encodeURIComponent(symbol)}`)

    if (!response.ok) {
      throw new Error(`Failed to fetch market data: ${response.status} ${response.statusText}`)
    }

    return response.json()
  },

  // Get historical data for charts (for future implementation)
  getHistoricalData: async (symbol: string, period: string = "1M"): Promise<any> => {
    // This would integrate with a historical data API
    // For now, return mock data
    return {
      symbol,
      period,
      data: []
    }
  }
}
