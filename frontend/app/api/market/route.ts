import { NextRequest, NextResponse } from "next/server"
import { exec } from "child_process"
import { promisify } from "util"
import path from "path"

const execAsync = promisify(exec)

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const symbol = searchParams.get("symbol")

    if (!symbol) {
      return NextResponse.json({ error: "Symbol parameter is required" }, { status: 400 })
    }

    // Get the backend directory path
    const backendPath = path.join(process.cwd(), "..", "backend")

    // Run the Django management command to get stock prices from database
    try {
      const { stdout, stderr } = await execAsync(
        `python manage.py shell -c "
from aut.mongodb_client import get_db
import json
db = get_db()
stock_prices_collection = db['stock_prices']
stock = stock_prices_collection.find_one({'symbol': '${symbol}'})
if stock:
    result = {
        'symbol': stock['symbol'],
        'name': stock.get('name', stock['symbol']),
        'currentPrice': stock['current_price'],
        'change': stock['change'],
        'changePercent': stock['change_percent'],
        'volume': stock.get('volume', 0),
        'lastUpdated': stock['timestamp'].isoformat() if stock.get('timestamp') else None
    }
    print(json.dumps(result))
else:
    print('null')
"`,
        {
          cwd: backendPath,
          timeout: 10000, // 10 seconds timeout
          maxBuffer: 1024 * 1024 // 1MB buffer
        }
      )

      const result = stdout.trim()
      if (result && result !== 'null') {
        // Extract JSON from output (handle Django shell output that may include extra text)
        const jsonMatch = result.match(/\{[\s\S]*\}/)
        if (jsonMatch) {
          try {
            const stockData = JSON.parse(jsonMatch[0])
            return NextResponse.json(stockData)
          } catch (parseError) {
            console.log("JSON parse error:", parseError, "Raw output:", result)
          }
        } else {
          console.log("No JSON found in output:", result)
        }
      }
    } catch (dbError) {
      console.log("Database query failed, falling back to APIs:", dbError)
    }

    // Fallback to original API logic if database query fails
    // For NIFTY 50, use NSE API or Yahoo Finance
    if (symbol === "NIFTY 50") {
      try {
        // Try NSE API first
        const nseResponse = await fetch(`https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050`, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
          }
        })

        if (nseResponse.ok) {
          const data = await nseResponse.json()
          const niftyData = data.data?.[0]

          if (niftyData) {
            return NextResponse.json({
              symbol: "NIFTY 50",
              name: "National Stock Exchange of India Index",
              currentPrice: parseFloat(niftyData.lastPrice || niftyData.last) || 22450.25,
              change: parseFloat(niftyData.change || niftyData.netChange) || 125.75,
              changePercent: parseFloat(niftyData.pChange || niftyData.perChange) || 0.56,
              open: parseFloat(niftyData.open),
              high: parseFloat(niftyData.dayHigh),
              low: parseFloat(niftyData.dayLow),
              volume: parseFloat(niftyData.totalTradedVolume),
              lastUpdated: new Date().toISOString()
            })
          }
        }
      } catch (nseError) {
        console.log("NSE API failed, trying Yahoo Finance")
      }

      // Fallback to Yahoo Finance
      try {
        const yahooResponse = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?period1=${Math.floor(Date.now() / 1000) - 86400}&period2=${Math.floor(Date.now() / 1000)}&interval=1d`)

        if (yahooResponse.ok) {
          const data = await yahooResponse.json()
          const chart = data.chart?.result?.[0]
          const meta = chart?.meta

          if (meta) {
            const previousClose = meta.previousClose || meta.chartPreviousClose
            const currentPrice = meta.regularMarketPrice || previousClose
            const change = currentPrice - previousClose
            const changePercent = (change / previousClose) * 100

            return NextResponse.json({
              symbol: "NIFTY 50",
              name: "National Stock Exchange of India Index",
              currentPrice: currentPrice,
              change: change,
              changePercent: changePercent,
              open: meta.regularMarketOpen,
              high: meta.regularMarketDayHigh,
              low: meta.regularMarketDayLow,
              volume: meta.regularMarketVolume,
              lastUpdated: new Date().toISOString()
            })
          }
        }
      } catch (yahooError) {
        console.log("Yahoo Finance API failed")
      }
    }

    // For individual stocks, try Yahoo Finance
    try {
      const yahooSymbol = symbol === "NIFTY 50" ? "%5ENSEI" : `${symbol}.NS`
      const yahooResponse = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${yahooSymbol}?period1=${Math.floor(Date.now() / 1000) - 86400}&period2=${Math.floor(Date.now() / 1000)}&interval=1d`)

      if (yahooResponse.ok) {
        const data = await yahooResponse.json()
        const chart = data.chart?.result?.[0]
        const meta = chart?.meta

        if (meta) {
          const previousClose = meta.previousClose || meta.chartPreviousClose
          const currentPrice = meta.regularMarketPrice || previousClose
          const change = currentPrice - previousClose
          const changePercent = (change / previousClose) * 100

          return NextResponse.json({
            symbol: symbol,
            name: meta.shortName || meta.longName || symbol,
            currentPrice: currentPrice,
            change: change,
            changePercent: changePercent,
            open: meta.regularMarketOpen,
            high: meta.regularMarketDayHigh,
            low: meta.regularMarketDayLow,
            volume: meta.regularMarketVolume,
            lastUpdated: new Date().toISOString()
          })
        }
      }
    } catch (error) {
      console.log("Yahoo Finance API failed for", symbol)
    }

    // Fallback to sample data if APIs fail - including Indian stocks
    const sampleData = {
      "NIFTY 50": {
        symbol: "NIFTY 50",
        name: "National Stock Exchange of India Index",
        currentPrice: 22450.25,
        change: 125.75,
        changePercent: 0.56,
      },
      "RELIANCE": {
        symbol: "RELIANCE",
        name: "Reliance Industries Limited",
        currentPrice: 1398.30,
        change: 15.20,
        changePercent: 1.10,
      },
      "TCS": {
        symbol: "TCS",
        name: "Tata Consultancy Services Limited",
        currentPrice: 3456.75,
        change: -12.45,
        changePercent: -0.36,
      },
      "INFY": {
        symbol: "INFY",
        name: "Infosys Limited",
        currentPrice: 1567.80,
        change: 8.90,
        changePercent: 0.57,
      },
      "HDFCBANK": {
        symbol: "HDFCBANK",
        name: "HDFC Bank Limited",
        currentPrice: 1789.45,
        change: 23.60,
        changePercent: 1.34,
      },
      "ICICIBANK": {
        symbol: "ICICIBANK",
        name: "ICICI Bank Limited",
        currentPrice: 987.65,
        change: -5.40,
        changePercent: -0.54,
      },
      "HINDUNILVR": {
        symbol: "HINDUNILVR",
        name: "Hindustan Unilever Limited",
        currentPrice: 2345.60,
        change: 18.75,
        changePercent: 0.81,
      },
      "ITC": {
        symbol: "ITC",
        name: "ITC Limited",
        currentPrice: 456.78,
        change: 3.25,
        changePercent: 0.72,
      },
      "KOTAKBANK": {
        symbol: "KOTAKBANK",
        name: "Kotak Mahindra Bank Limited",
        currentPrice: 1890.90,
        change: -8.15,
        changePercent: -0.43,
      },
      "LT": {
        symbol: "LT",
        name: "Larsen & Toubro Limited",
        currentPrice: 2876.45,
        change: 42.30,
        changePercent: 1.49,
      },
      "BAJFINANCE": {
        symbol: "BAJFINANCE",
        name: "Bajaj Finance Limited",
        currentPrice: 6789.12,
        change: 156.80,
        changePercent: 2.36,
      },
      "BHARTIARTL": {
        symbol: "BHARTIARTL",
        name: "Bharti Airtel Limited",
        currentPrice: 1234.56,
        change: -7.89,
        changePercent: -0.63,
      },
      "MARUTI": {
        symbol: "MARUTI",
        name: "Maruti Suzuki India Limited",
        currentPrice: 9876.54,
        change: 123.45,
        changePercent: 1.26,
      },
      "AXISBANK": {
        symbol: "AXISBANK",
        name: "Axis Bank Limited",
        currentPrice: 876.54,
        change: 12.34,
        changePercent: 1.43,
      },
      "BAJAJ-AUTO": {
        symbol: "BAJAJ-AUTO",
        name: "Bajaj Auto Limited",
        currentPrice: 5432.10,
        change: -67.89,
        changePercent: -1.23,
      },
      "HCLTECH": {
        symbol: "HCLTECH",
        name: "HCL Technologies Limited",
        currentPrice: 1234.56,
        change: 23.45,
        changePercent: 1.94,
      },
      "WIPRO": {
        symbol: "WIPRO",
        name: "Wipro Limited",
        currentPrice: 345.67,
        change: -2.34,
        changePercent: -0.67,
      },
      "NTPC": {
        symbol: "NTPC",
        name: "NTPC Limited",
        currentPrice: 234.56,
        change: 4.56,
        changePercent: 1.98,
      },
      "POWERGRID": {
        symbol: "POWERGRID",
        name: "Power Grid Corporation of India Limited",
        currentPrice: 187.65,
        change: 2.34,
        changePercent: 1.26,
      },
      "ONGC": {
        symbol: "ONGC",
        name: "Oil and Natural Gas Corporation Limited",
        currentPrice: 156.78,
        change: -1.23,
        changePercent: -0.78,
      },
      "COALINDIA": {
        symbol: "COALINDIA",
        name: "Coal India Limited",
        currentPrice: 298.76,
        change: 5.67,
        changePercent: 1.94,
      },
      "GRASIM": {
        symbol: "GRASIM",
        name: "Grasim Industries Limited",
        currentPrice: 1876.54,
        change: 23.45,
        changePercent: 1.27,
      },
      "ULTRACEMCO": {
        symbol: "ULTRACEMCO",
        name: "UltraTech Cement Limited",
        currentPrice: 7654.32,
        change: 98.76,
        changePercent: 1.31,
      },
      "NESTLEIND": {
        symbol: "NESTLEIND",
        name: "Nestle India Limited",
        currentPrice: 19876.54,
        change: 234.56,
        changePercent: 1.19,
      },
      "BRITANNIA": {
        symbol: "BRITANNIA",
        name: "Britannia Industries Limited",
        currentPrice: 4567.89,
        change: -34.56,
        changePercent: -0.75,
      },
      "HEROMOTOCO": {
        symbol: "HEROMOTOCO",
        name: "Hero MotoCorp Limited",
        currentPrice: 3456.78,
        change: 45.67,
        changePercent: 1.34,
      },
      "DRREDDY": {
        symbol: "DRREDDY",
        name: "Dr. Reddy's Laboratories Limited",
        currentPrice: 5678.90,
        change: 67.89,
        changePercent: 1.21,
      },
      "CIPLA": {
        symbol: "CIPLA",
        name: "Cipla Limited",
        currentPrice: 1234.56,
        change: -12.34,
        changePercent: -0.99,
      },
      "SUNPHARMA": {
        symbol: "SUNPHARMA",
        name: "Sun Pharmaceutical Industries Limited",
        currentPrice: 1098.76,
        change: 23.45,
        changePercent: 2.18,
      },
      "TATAMOTORS": {
        symbol: "TATAMOTORS",
        name: "Tata Motors Limited",
        currentPrice: 678.90,
        change: -8.76,
        changePercent: -1.27,
      },
      "M&M": {
        symbol: "M&M",
        name: "Mahindra & Mahindra Limited",
        currentPrice: 1876.54,
        change: 34.56,
        changePercent: 1.88,
      },
      "AAPL": {
        symbol: "AAPL",
        name: "Apple Inc.",
        currentPrice: 187.32,
        change: 1.25,
        changePercent: 0.67,
      },
      "MSFT": {
        symbol: "MSFT",
        name: "Microsoft Corporation",
        currentPrice: 415.5,
        change: 2.1,
        changePercent: 0.51,
      },
      "GOOGL": {
        symbol: "GOOGL",
        name: "Alphabet Inc.",
        currentPrice: 175.2,
        change: 0.5,
        changePercent: 0.29,
      },
      "AMZN": {
        symbol: "AMZN",
        name: "Amazon.com, Inc.",
        currentPrice: 185.95,
        change: -1.2,
        changePercent: -0.64,
      },
      "NVDA": {
        symbol: "NVDA",
        name: "NVIDIA Corporation",
        currentPrice: 950.02,
        change: -0.75,
        changePercent: -0.08,
      },
    }

    const fallbackData = sampleData[symbol as keyof typeof sampleData] || {
      symbol: symbol,
      name: `${symbol} Stock`,
      currentPrice: 100,
      change: 0,
      changePercent: 0,
    }

    return NextResponse.json({
      ...fallbackData,
      lastUpdated: new Date().toISOString(),
      note: "Using fallback data - APIs may be unavailable"
    })

  } catch (error) {
    console.error("Error fetching market data:", error)
    return NextResponse.json({ error: "Failed to fetch market data" }, { status: 500 })
  }
}
