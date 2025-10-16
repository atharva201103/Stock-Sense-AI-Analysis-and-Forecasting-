"use client"

import { DashboardLayout } from "@/components/dashboard/dashboard-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Bell, AlertTriangle, TrendingUp, TrendingDown } from "lucide-react"
import { useEffect, useState } from "react"

interface Alert {
  stock: string
  nature: string
  sentiment: number
  message: string
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchAlerts = async () => {
      const token = localStorage.getItem('access_token')
      if (!token) {
        setLoading(false)
        return
      }

      try {
        const response = await fetch('http://127.0.0.1:8000/api/user/alerts/', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        })

        if (response.ok) {
          const data = await response.json()
          if (data.success) {
            setAlerts(data.alerts)
          }
        }
      } catch (error) {
        console.error('Error fetching alerts:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchAlerts()
  }, [])

  const getAlertIcon = (nature: string) => {
    if (nature === 'Negative') {
      return <AlertTriangle className="h-5 w-5" />
    } else if (nature === 'Positive') {
      return <TrendingUp className="h-5 w-5" />
    } else {
      return <Bell className="h-5 w-5" />
    }
  }

  const getAlertColor = (nature: string) => {
    if (nature === 'Negative') {
      return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300"
    } else if (nature === 'Positive') {
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300"
    } else {
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300"
    }
  }

  if (loading) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <p>Loading alerts...</p>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Alerts</h1>
      </div>

      <div className="space-y-4">
        {alerts.length > 0 ? (
          alerts.map((alert, index) => (
            <Card key={index}>
              <CardContent className="pt-6">
                <div className="flex items-start space-x-4">
                  <div className={`p-2 rounded-full ${getAlertColor(alert.nature)}`}>
                    {getAlertIcon(alert.nature)}
                  </div>
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold">{alert.stock} Alert</h3>
                      <Badge variant="destructive">
                        {alert.nature}
                      </Badge>
                    </div>
                    <p className="text-muted-foreground">{alert.message}</p>
                    <p className="text-sm text-muted-foreground">Sentiment Score: {alert.sentiment.toFixed(2)}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        ) : (
          <Card>
            <CardContent className="pt-6">
              <div className="text-center py-8">
                <Bell className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">No alerts</h3>
                <p className="text-muted-foreground">
                  Your portfolio stocks have positive sentiment. No alerts at this time.
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  )
}
