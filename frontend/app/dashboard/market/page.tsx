"use client"

import { useEffect, useState } from "react"
import { DashboardLayout } from "@/components/dashboard/dashboard-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertCircle, TrendingUp, TrendingDown, RefreshCw } from "lucide-react"
import { MarketService, type MarketData } from "@/services/market-service"
import { useToast } from "@/hooks/use-toast"

// Common Indian stocks
const INDIAN_STOCKS = [
  "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR",
  "ITC", "KOTAKBANK", "LT", "AXISBANK", "MARUTI", "BAJFINANCE",
  "BHARTIARTL", "WIPRO", "ULTRACEMCO", "NESTLEIND", "POWERGRID", "NTPC"
]

export default function MarketPage() {
  const { toast } = useToast()
  const [stocks, setStocks] = useState<MarketData[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetchStocksData = async () => {
    setLoading(true)
    setError(null)

    try {
      const stockPromises = INDIAN_STOCKS.map(symbol => MarketService.getMarketData(symbol))
      const stocksData = await Promise.all(stockPromises)
      setStocks(stocksData)
    } catch (err) {
      console.error("Error fetching stocks data:", err)
      setError("Failed to load market data. Please try again later.")
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      const accessToken = localStorage.getItem("accessToken")
      if (!accessToken) {
        throw new Error("No access token found")
      }

      // Trigger scrape
      const scrapeResponse = await fetch("/api/market/refresh", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })

      if (!scrapeResponse.ok) {
        throw new Error("Failed to refresh market data")
      }

      const scrapeData = await scrapeResponse.json()
      if (!scrapeData.success) {
        throw new Error(scrapeData.error || "Failed to refresh market data")
      }

      toast({
        title: "Market data refreshed",
        description: scrapeData.message,
      })

      // Then fetch the new data
      await fetchStocksData()
    } catch (error) {
      console.error("Error refreshing market data:", error)
      toast({
        title: "Refresh failed",
        description: "Failed to refresh market data. Please try again.",
        variant: "destructive",
      })
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchStocksData()

    // Refresh data every 5 minutes
    const interval = setInterval(fetchStocksData, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  const handleTradeStock = (symbol: string) => {
    window.location.href = `/dashboard/trade?symbol=${symbol}`
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold">Indian Market</h1>
            <p className="text-muted-foreground">Real-time data for major Indian stocks</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 18 }).map((_, i) => (
              <Card key={i}>
                <CardHeader className="pb-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-3 w-32" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-8 w-20 mb-2" />
                  <Skeleton className="h-4 w-16" />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </DashboardLayout>
    )
  }

  if (error) {
    return (
      <DashboardLayout>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Indian Market</h1>
            <p className="text-muted-foreground">Real-time data for major Indian stocks</p>
          </div>
          <Button variant="outline" size="icon" onClick={handleRefresh} disabled={loading || refreshing}>
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            <span className="sr-only">Refresh market data</span>
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {stocks.map((stock) => {
            const isPositive = stock.change >= 0
            return (
              <Card key={stock.symbol} className="hover:shadow-md transition-shadow">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-semibold">{stock.symbol}</CardTitle>
                    {isPositive ? (
                      <TrendingUp className="h-4 w-4 text-green-500" />
                    ) : (
                      <TrendingDown className="h-4 w-4 text-red-500" />
                    )}
                  </div>
                  <CardDescription className="text-sm">{stock.name}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="text-2xl font-bold">₹{stock.currentPrice.toFixed(2)}</div>
                    <div className="flex items-center space-x-2">
                      <Badge variant={isPositive ? "default" : "destructive"} className="text-xs">
                        {isPositive ? "+" : ""}{stock.change.toFixed(2)} ({isPositive ? "+" : ""}{stock.changePercent.toFixed(2)}%)
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Last updated: {new Date(stock.lastUpdated).toLocaleTimeString()}
                    </div>
                    <Button
                      size="sm"
                      className="w-full mt-2"
                      onClick={() => handleTradeStock(stock.symbol)}
                    >
                      Trade {stock.symbol}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>

        <div className="text-center text-sm text-muted-foreground">
          Data refreshes every 5 minutes. Click on any stock to view detailed chart and trade.
        </div>
      </div>
    </DashboardLayout>
  )
}
