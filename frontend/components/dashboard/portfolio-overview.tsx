"use client"

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

// Colors for the pie chart
const COLORS = ["#4f46e5", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316"]

interface PortfolioOverviewProps {
  portfolioData?: any
}

export function PortfolioOverview({ portfolioData }: PortfolioOverviewProps) {
  // Use provided data
  const rawData = portfolioData?.portfolio?.holdings || []

  if (rawData.length === 0) {
    return (
      <Card className="col-span-2">
        <CardHeader>
          <CardTitle>Portfolio Overview</CardTitle>
          <CardDescription>Your current holdings and allocation</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <p className="text-muted-foreground">No portfolio holdings yet. Start trading to build your portfolio.</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // Transform data with mock current prices
  const data = rawData.map((stock: any) => {
    const priceVariation = Math.random() * 0.2 - 0.1 // -10% to +10%
    const currentPrice = stock.avgPrice * (1 + priceVariation)
    const changePercent = Math.random() * 4 - 2 // -2% to +2%
    return {
      name: stock.name || stock.symbol,
      shares: stock.shares,
      price: currentPrice,
      change: changePercent,
    }
  })

  // Calculate total value and percentages for pie chart
  const totalValue = data.reduce((sum: number, stock: any) => sum + stock.shares * stock.price, 0)

  // Create data for pie chart with correct percentages
  const pieData = data.map((stock: any) => {
    const stockValue = stock.shares * stock.price
    const percentage = (stockValue / totalValue) * 100
    return {
      ...stock,
      value: Math.round(percentage), // Use percentage for pie chart
    }
  })

  return (
    <Card className="col-span-2">
      <CardHeader>
        <CardTitle>Portfolio Overview</CardTitle>
        <CardDescription>Your current holdings and allocation</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div className="flex flex-col items-center justify-center">
            <div className="h-60 w-60">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {pieData.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value) => [`${value}%`, "Allocation"]}
                    labelFormatter={(index) => pieData[index as number].name}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 text-center">
              <div className="text-sm text-muted-foreground">Total Portfolio Value</div>
              <div className="text-2xl font-bold">₹{totalValue.toFixed(2)}</div>
            </div>
          </div>
          <div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead className="text-right">Shares</TableHead>
                  <TableHead className="text-right">Price</TableHead>
                  <TableHead className="text-right">Value</TableHead>
                  <TableHead className="text-right">Change</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((stock: any) => (
                  <TableRow key={stock.name}>
                    <TableCell className="font-medium">{stock.name}</TableCell>
                    <TableCell className="text-right">{stock.shares}</TableCell>
                    <TableCell className="text-right">₹{stock.price.toFixed(2)}</TableCell>
                    <TableCell className="text-right">₹{(stock.shares * stock.price).toFixed(2)}</TableCell>
                    <TableCell className={`text-right ${stock.change >= 0 ? "text-green-500" : "text-red-500"}`}>
                      {stock.change >= 0 ? "+" : ""}
                      {stock.change}%
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
