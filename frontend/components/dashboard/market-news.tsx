"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { RefreshCw } from "lucide-react"
import { useToast } from "@/hooks/use-toast"

interface NewsItem {
  id: string
  title: string
  content: string
  summary?: string
  source: string
  date: string
  url?: string
  category?: string
  tags?: string[]
  // Sentiment analysis fields
  sentimentScore?: number
  sentimentLabel?: string
  sentimentConfidence?: number
  // Additional processed fields
  natureOfNews?: string
  sectorOfCompany?: string
  impactLevel?: string
  stockMentioned?: string
  newsType?: string[]
  keywords?: string[]
  volatilityIndicator?: string
  relevanceScore?: number
  competitorImpact?: string
  marketTrendAlignment?: string
  regulatoryImpact?: string
  socialMediaBuzz?: string
  financialMetricsMentioned?: string[]
}

export function MarketNews() {
  const { toast } = useToast()
  const [news, setNews] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetchNews = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch news from API route
      const accessToken = localStorage.getItem("accessToken")
      if (!accessToken) {
        throw new Error("No access token found")
      }

      const response = await fetch("/api/news", {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })

      if (!response.ok) {
        throw new Error("Failed to fetch news")
      }

      const data = await response.json()
      console.log("News data:", data)

      if (!data.success) {
        throw new Error(data.error || "Failed to fetch news")
      }

      setNews(data.news || [])
    } catch (error) {
      console.error("Error fetching news:", error)
      setError("Failed to load news. Please try again later.")
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchNews()
  }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      const accessToken = localStorage.getItem("accessToken")
      if (!accessToken) {
        throw new Error("No access token found")
      }

      // Trigger scrape
      const scrapeResponse = await fetch("/api/news/refresh", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      })

      if (!scrapeResponse.ok) {
        throw new Error("Failed to refresh news")
      }

      const scrapeData = await scrapeResponse.json()
      if (!scrapeData.success) {
        throw new Error(scrapeData.error || "Failed to refresh news")
      }

      toast({
        title: "News refreshed",
        description: scrapeData.message,
      })

      // Then fetch the new news
      await fetchNews()
    } catch (error) {
      console.error("Error refreshing news:", error)
      toast({
        title: "Refresh failed",
        description: "Failed to refresh news. Please try again.",
        variant: "destructive",
      })
      setRefreshing(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    if (!date || isNaN(date.getTime())) {
      return "Recently"
    }
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))

    if (diffInHours < 1) {
      return "Just now"
    } else if (diffInHours < 24) {
      return `${diffInHours} ${diffInHours === 1 ? "hour" : "hours"} ago`
    } else {
      return date.toLocaleDateString()
    }
  }

  return (
    <Card className="col-span-2">
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Market News</CardTitle>
          <CardDescription>Latest financial news and updates</CardDescription>
        </div>
        <Button variant="outline" size="icon" onClick={handleRefresh} disabled={loading || refreshing}>
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          <span className="sr-only">Refresh</span>
        </Button>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[600px] pr-4">
          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="border-b pb-4 last:border-0">
                  <Skeleton className="h-5 w-3/4 mb-2" />
                  <Skeleton className="h-3 w-1/3 mb-2" />
                  <Skeleton className="h-4 w-full mb-1" />
                  <Skeleton className="h-4 w-full mb-1" />
                  <Skeleton className="h-4 w-2/3" />
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="flex h-full items-center justify-center text-center text-muted-foreground">
              <p>{error}</p>
            </div>
          ) : (
            <div className="space-y-4">
              {news.length === 0 ? (
                <div className="flex h-full items-center justify-center text-center text-muted-foreground">
                  <p>No news available at the moment.</p>
                </div>
              ) : (
                news.map((item) => (
                  <div key={item.id} className="border-b pb-4 last:border-0">
                    <h3 className="font-semibold">{item.title}</h3>
                    <div className="mt-1 flex items-center text-xs text-muted-foreground">
                      <span>{item.source}</span>
                      <span className="mx-2">•</span>
                      <span>{formatDate(item.date)}</span>
                    </div>
                    <p className="mt-2 text-sm">{item.summary || item.content}</p>

                    {/* Sentiment Analysis Display */}
                    {item.sentimentLabel && (
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-xs font-medium">Sentiment:</span>
                        <span
                          className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${
                            item.sentimentLabel === 'positive'
                              ? 'bg-green-100 text-green-800'
                              : item.sentimentLabel === 'negative'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {item.sentimentLabel.charAt(0).toUpperCase() + item.sentimentLabel.slice(1)}
                          {item.sentimentConfidence && (
                            <span className="ml-1 opacity-75">
                              ({Math.round(item.sentimentConfidence * 100)}%)
                            </span>
                          )}
                        </span>
                      </div>
                    )}

                    {/* Additional Metadata */}
                    <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                      {item.impactLevel && item.impactLevel !== 'Medium' && (
                        <span>Impact: {item.impactLevel}</span>
                      )}
                      {item.volatilityIndicator && item.volatilityIndicator !== 'Medium' && (
                        <span>Volatility: {item.volatilityIndicator}</span>
                      )}
                      {item.relevanceScore && item.relevanceScore !== 5 && (
                        <span>Relevance: {item.relevanceScore}/10</span>
                      )}
                      {item.natureOfNews && item.natureOfNews !== 'Neutral' && (
                        <span>Nature: {item.natureOfNews}</span>
                      )}
                      {item.sectorOfCompany && item.sectorOfCompany !== 'General' && (
                        <span>Sector: {item.sectorOfCompany}</span>
                      )}
                    </div>

                    {/* Keywords */}
                    {item.keywords && item.keywords.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {item.keywords.slice(0, 3).map((keyword, idx) => (
                          <span key={idx} className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                            {keyword}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Stock Mentioned */}
                    {item.stockMentioned && item.stockMentioned !== 'General' && (
                      <div className="mt-1 text-xs text-muted-foreground">
                        Stock: {item.stockMentioned}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
