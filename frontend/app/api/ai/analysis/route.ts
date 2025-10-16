import { NextResponse } from "next/server"
import { connectToDatabase, disconnectFromDatabase } from "@/lib/mongodb"
import { COLLECTIONS } from "@/lib/mongodb-schemas"
import { verifyToken } from "@/lib/auth-utils"
import { getUserContext } from "@/lib/user-context"

export async function GET(request: Request) {
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

    const { db } = await connectToDatabase()

    // Get latest news from raw_news collection
    const newsCollection = db.collection("raw_news")
    const latestNews = await newsCollection.find().sort({ date: -1 }).limit(3).toArray()

    // Get user context
    const userContext = await getUserContext(userData.id.toString(), db)

    // Create prompt for market analysis
    const prompt = `
      You are a financial analyst providing a daily market analysis. 
      
      Here are the latest news items:
      ${latestNews.map((news) => `- ${news.title}: ${news.content}`).join("\n")}
      
      User information:
      ${JSON.stringify(userContext, null, 2)}
      
      Based on the above information, provide a concise daily market analysis focusing on:
      1. Key market trends
      2. Potential impact on the user's portfolio
      3. Actionable insights or recommendations
      
      Format your response in a professional, easy-to-read manner with clear sections.
    `

    // Call Ollama API
    const ollamaResponse = await fetch("http://localhost:11434/api/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "deepseek-r1:1.5b",
        prompt: prompt,
        stream: false,
      }),
    })

    let ollamaData = null
    if (ollamaResponse.ok) {
      ollamaData = await ollamaResponse.json()
    }

    if (ollamaData) {
      // Remove the <think> section from DeepSeek response
      let analysis = ollamaData.response
      const thinkStart = analysis.indexOf('<think>')
      const thinkEnd = analysis.indexOf('</think>')
      if (thinkStart !== -1 && thinkEnd !== -1) {
        analysis = analysis.substring(thinkEnd + 8).trim() // Remove <think> to </think> and trim
      }
      return NextResponse.json({
        success: true,
        analysis: analysis,
      })
    } else {
      // Fallback analysis if AI service fails - include latest news
      const newsText = latestNews.length > 0
        ? latestNews.map((news) => `- ${news.title}`).join("\n")
        : "No recent news available."

      const fallbackAnalysis = `
        # Daily Market Analysis

        ## Latest News Summary
        ${newsText}

        ## Market Overview
        Markets are showing mixed signals today with technology stocks leading gains while energy sectors face pressure from changing commodity prices.

        ## Key Trends
        - Tech sector continues to show resilience amid economic uncertainty
        - Interest rate expectations are shifting as new economic data emerges
        - Global supply chains are stabilizing, potentially easing inflationary pressures

        ## Recommendations
        Consider maintaining a diversified portfolio with exposure to both growth and value stocks. The current environment favors quality companies with strong balance sheets and consistent cash flows.
      `

      return NextResponse.json({
        success: true,
        analysis: fallbackAnalysis,
        fallback: true,
      })
    }
  } catch (error) {
    console.error("Error generating market analysis:", error)

    // Fallback analysis if any error occurs
    const fallbackAnalysis = `
      # Daily Market Analysis

      ## Market Overview
      Markets are showing mixed signals today with technology stocks leading gains while energy sectors face pressure from changing commodity prices.

      ## Key Trends
      - Tech sector continues to show resilience amid economic uncertainty
      - Interest rate expectations are shifting as new economic data emerges
      - Global supply chains are stabilizing, potentially easing inflationary pressures

      ## Recommendations
      Consider maintaining a diversified portfolio with exposure to both growth and value stocks. The current environment favors quality companies with strong balance sheets and consistent cash flows.
    `

    return NextResponse.json({
      success: true,
      analysis: fallbackAnalysis,
      fallback: true,
    })
  } finally {
    await disconnectFromDatabase()
  }
}
