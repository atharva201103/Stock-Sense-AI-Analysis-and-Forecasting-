"use client"

import { DashboardLayout } from "@/components/dashboard/dashboard-layout"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Bell, AlertTriangle, TrendingUp, TrendingDown } from "lucide-react"
import { useEffect, useState } from "react"

interface Alert {
  id: string
  stock: string
  alert_type: string
  message: string
  sentiment_score: number
  predicted_nature: string
  created_at: string
  is_read: boolean
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchAlerts = async () => {
      const token = localStorage.getItem('accessToken') || localStorage.getItem('access_token')
      if (!token) {
        setLoading(false)
        return
      }

      try {
        const response = await fetch('http://127.0.0.1:8001/api/user/alerts/', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        })

        if (response.ok) {
          const data = await response.json()
          if (data.success) {
            setAlerts(data.alerts)
          }
        } else {
          console.error('Failed to fetch alerts:', response.status, response.statusText)
        }
      } catch (error) {
        console.error('Error fetching alerts:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchAlerts()
  }, [])

  const getAlertIcon = (predicted_nature: string) => {
    if (predicted_nature === 'Negative') {
      return <AlertTriangle className="h-5 w-5" />
    } else if (predicted_nature === 'Positive') {
      return <TrendingUp className="h-5 w-5" />
    } else {
      return <Bell className="h-5 w-5" />
    }
  }

  const getAlertColor = (predicted_nature: string) => {
    if (predicted_nature === 'Negative') {
      return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300"
    } else if (predicted_nature === 'Positive') {
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300"
    } else {
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300"
    }
  }

  const markAsRead = async (alertId: string) => {
    const token = localStorage.getItem('accessToken') || localStorage.getItem('access_token')
    if (!token) return

    try {
      const response = await fetch('http://127.0.0.1:8001/api/user/alerts/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ alert_id: alertId }),
      })

      if (response.ok) {
        // Update local state to mark as read
        setAlerts(alerts.map(alert =>
          alert.id === alertId ? { ...alert, is_read: true } : alert
        ))
      } else {
        console.error('Failed to mark alert as read:', response.status, response.statusText)
      }
    } catch (error) {
      console.error('Error marking alert as read:', error)
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
          alerts.map((alert) => (
            <Card key={alert.id}>
              <CardContent className="pt-6">
                <div className="flex items-start space-x-4">
                  <div className={`p-2 rounded-full ${getAlertColor(alert.predicted_nature)}`}>
                    {getAlertIcon(alert.predicted_nature)}
                  </div>
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center justify-between">
                      <h3 className="font-semibold">{alert.stock} Alert</h3>
                      <div className="flex items-center space-x-2">
                        <Badge variant={alert.predicted_nature === 'Negative' ? 'destructive' : 'default'}>
                          {alert.predicted_nature}
                        </Badge>
                        {!alert.is_read && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => markAsRead(alert.id)}
                          >
                            Mark as Read
                          </Button>
                        )}
                      </div>
                    </div>
                    <p className="text-muted-foreground">{alert.message}</p>
                    <p className="text-sm text-muted-foreground">Sentiment Score: {alert.sentiment_score.toFixed(2)}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(alert.created_at).toLocaleString()}
                    </p>
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
