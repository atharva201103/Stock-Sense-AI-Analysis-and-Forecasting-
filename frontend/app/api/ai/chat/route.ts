import { NextResponse } from "next/server"
import { connectToDatabase, disconnectFromDatabase } from "@/lib/mongodb"
import { COLLECTIONS } from "@/lib/mongodb-schemas"
import { verifyToken } from "@/lib/auth-utils"
import { getUserContext } from "@/lib/user-context"

export async function POST(request: Request) {
  try {
    // Verify JWT token
    const token = request.headers.get("Authorization")?.replace("Bearer ", "")
    if (!token) {
      return NextResponse.json({ success: false, error: "Unauthorized" }, { status: 401 })
    }

    const userData = await verifyToken(token)
    if (!userData) {
      return NextResponse.json({ success: false, error: "Invalid token" }, { status: 401 })
    }
    console.log("AI chat: userData.id =", userData.id)

    const body = await request.json()
    const { message } = body

    if (!message) {
      return NextResponse.json({ success: false, error: "Message is required" }, { status: 400 })
    }

    const { db } = await connectToDatabase()

    // Get user context
    const userContext = await getUserContext(userData.id.toString(), db)
    console.log("User context for AI:", JSON.stringify(userContext, null, 2))

    // Scrape news if message is about news
    let newsText = ''
    if (message.toLowerCase().includes('news')) {
      try {
        const newsResponse = await fetch('https://www.moneycontrol.com/news/business/stocks/')
        const newsHtml = await newsResponse.text()
        // Simple parsing - in production, use a proper scraper
        const titleMatches = newsHtml.match(/<h2[^>]*>(.*?)<\/h2>/g) || []
        const titles = titleMatches.slice(0, 5).map(match => match.replace(/<[^>]*>/g, '').trim())
        newsText = titles.length > 0 ? `\n\nRecent Stock News:\n${titles.map(title => `- ${title}`).join('\n')}` : ''
      } catch (error) {
        console.error('Error scraping news:', error)
      }
    }

    // Add technical analysis if message is about portfolio or advice
    let technicalText = ''
    if ((message.toLowerCase().includes('portfolio') || message.toLowerCase().includes('advice') || message.toLowerCase().includes('analysis')) && userContext.portfolio?.length > 0) {
      technicalText = '\n\nTechnical Analysis for Portfolio Stocks:\n'
      for (const stock of userContext.portfolio) {
        // Mock calculations - in production, use real data
        const mockPrices = Array.from({length: 50}, () => stock.avgPrice + (Math.random() - 0.5) * stock.avgPrice * 0.2)
        const sma20 = mockPrices.slice(-20).reduce((a, b) => a + b, 0) / 20
        const sma50 = mockPrices.reduce((a, b) => a + b, 0) / 50
        const gains = mockPrices.slice(1).map((price, i) => price - mockPrices[i]).filter(g => g > 0)
        const losses = mockPrices.slice(1).map((price, i) => mockPrices[i] - price).filter(l => l > 0)
        const avgGain = gains.reduce((a, b) => a + b, 0) / gains.length || 0
        const avgLoss = losses.reduce((a, b) => a + b, 0) / losses.length || 0
        const rs = avgGain / avgLoss
        const rsi = 100 - (100 / (1 + rs))
        let signal = 'Hold'
        if (sma20 > sma50 && rsi < 70) signal = 'Buy'
        else if (sma20 < sma50 && rsi > 30) signal = 'Sell'
        technicalText += `- ${stock.symbol}: SMA20: ₹${sma20.toFixed(2)}, SMA50: ₹${sma50.toFixed(2)}, RSI: ${rsi.toFixed(2)}, Signal: ${signal}\n`
      }
    }

    // Create prompt with user context
    const contextText = `
User Information:
- Username: ${userContext.user?.username || 'Unknown'}
- Account Balance: ${userContext.user?.balance || '₹0'}

Portfolio Holdings:
${userContext.portfolio?.length > 0
  ? userContext.portfolio.map((h: any) => `- ${h.symbol}: ${h.shares} shares at average price ${h.avgPrice}, total cost ${h.totalCost}`).join('\n')
  : 'No stock holdings'}

Recent Transactions:
${userContext.recentTransactions?.length > 0
  ? userContext.recentTransactions.slice(0, 3).map((t: any) => `- ${t.type} ${t.shares} shares of ${t.symbol} at ${t.price} on ${t.date}`).join('\n')
  : 'No recent transactions'}

Watchlist:
${userContext.watchlist?.length > 0
  ? userContext.watchlist.map((s: any) => `- ${s.symbol}: ${s.name}`).join('\n')
  : 'No stocks in watchlist'}${newsText}${technicalText}
    `.trim()

    const prompt = `
You are Trada, an AI financial advisor and trading assistant specializing in Indian stock markets. You are helping a user with their investment questions.

Here is information about the user you are advising:

${contextText}

IMPORTANT GUIDELINES:
1. Always use ₹ (rupees) when discussing money or stock prices, not dollars.
2. Only recommend Indian stocks and financial products.
3. Use the user's portfolio, transaction history, and account balance to provide relevant advice.
4. If the user asks about specific stocks in their watchlist or portfolio, reference those specifically.
5. Keep your response under 200 words and focus on actionable insights.
6. Never mention that you are powered by any specific AI model.
7. Only generate a chart if the user explicitly asks for a chart, graph, visualization, or plot.
8. If generating a chart, create a matplotlib code block with appropriate labels, title, and styling.
9. For charts, use plt.figure(figsize=(10, 6)) and add proper grid lines, legends, and axis labels.
10. Only use matplotlib and numpy for charts. Do not import or use any other libraries like yfinance, pandas, or external data sources.
11. Create charts using sample or mock data if needed, based on the user's portfolio or general market knowledge.
12. When providing news, analyze the sentiment of each news item (positive, negative, or neutral) and include it.
13. For portfolio analysis, use technical indicators like Moving Averages (SMA 20, SMA 50) and RSI to suggest buy/sell/hold signals. Use mock price data for calculations.
14. Respond as Trada, addressing the user directly using "you" and "your" to refer to the user.

The user asks: "${message}"

As Trada, provide a helpful, accurate, and personalized response about Indian financial markets, trading, or investments.
If a chart is appropriate, generate matplotlib code to visualize the data.
    `

    // Call Django backend instead of Ollama directly
    const djangoResponse = await fetch("http://localhost:8000/model/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify({
        prompt: prompt,
      }),
    })

    if (!djangoResponse.ok) {
      throw new Error(`Django API error: ${djangoResponse.status}`)
    }

    const djangoData = await djangoResponse.json()

    // Store conversation in MongoDB
    const chatsCollection = db.collection(COLLECTIONS.CHAT_CONVERSATIONS)

    // Check for recent conversation (last 30 minutes)
    const thirtyMinutesAgo = new Date(Date.now() - 30 * 60 * 1000)
    const recentConversation = await chatsCollection.findOne({
      userId: userData.id.toString(),
      lastUpdated: { $gt: thirtyMinutesAgo },
    })

    const now = new Date()

    // Determine response type and content
    const responseType = djangoData.type || "text"
    const responseContent = djangoData.message || ""
    const imageUrl = djangoData.image_url || null

    const userMessage = {
      id: Date.now().toString(),
      content: message,
      role: "user" as const,
      timestamp: now,
      type: "text" as const,
    }

    const assistantMessage = {
      id: (Date.now() + 1).toString(),
      content: responseContent,
      role: "assistant" as const,
      timestamp: now,
      type: responseType as "text" | "image",
      ...(imageUrl && { imageUrl }),
    }

    if (recentConversation) {
      
      await chatsCollection.updateOne(
        { _id: recentConversation._id },
        {
          $push: {
            messages: { $each: [userMessage, assistantMessage] },
          } as any,
          $set: { lastUpdated: now },
        },
      )
    } else {
      // Create new conversation
      const firstUserMessage = message.slice(0, 30) + (message.length > 30 ? "..." : "")
      await chatsCollection.insertOne({
        id: Date.now().toString(),
        userId: userData.id.toString(),
        title: firstUserMessage,
        messages: [userMessage, assistantMessage],
        lastUpdated: now,
        createdAt: now,
      })
    }

   
    return NextResponse.json({
      success: true,
      type: djangoData.type,
      content: djangoData.message,
      image_url: djangoData.image_url,
    })
  } catch (error) {
    console.error("Error generating AI response:", error)

    // Fallback response if AI service fails
    const fallbackResponses = [
      "Based on recent market trends, RELIANCE shows strong potential for growth in the next quarter.",
      "I'd recommend diversifying your portfolio with some index funds to reduce risk exposure.",
      "The tech sector has been volatile lately, but TCS has shown resilience due to strong fundamentals.",
      "Looking at your portfolio, you might want to consider taking some profits from your top performers.",
      "Interest rate changes could impact banking stocks. Keep an eye on HDFC and ICICI Bank.",
    ]

    return NextResponse.json({
      success: true,
      type: "text",
      message: fallbackResponses[Math.floor(Math.random() * fallbackResponses.length)],
      fallback: true,
    })
  } finally {
    await disconnectFromDatabase()
  }
}
