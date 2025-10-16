import { NextResponse } from "next/server"
import { connectToDatabase, disconnectFromDatabase } from "@/lib/mongodb"
import { verifyToken } from "@/lib/auth-utils"
import * as cheerio from "cheerio"
import { randomUUID } from "crypto"

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

    const { db } = await connectToDatabase()

    const rawNewsCollection = db.collection("raw_news")

    const headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    // Scrape multiple pages
    const newsItems: any[] = []
    const pages = [1, 2, 3]
    for (const page of pages) {
      const url = page === 1 ? 'https://www.moneycontrol.com/news/business/stocks/' : `https://www.moneycontrol.com/news/business/stocks/page-${page}/`
      try {
        const response = await fetch(url, { headers })
        if (!response.ok) {
          console.error(`Failed to fetch page ${page}: ${response.status}`)
          continue
        }

        const html = await response.text()
        const $ = cheerio.load(html)

        $('a[href*="/news/business/stocks/"]').each((i, elem) => {
          const title = $(elem).text().trim()
          let link = $(elem).attr('href')
          if (link && link.startsWith('/')) {
            link = 'https://www.moneycontrol.com' + link
          }
          if (title && link && title.length > 10 && !title.includes('{') && !title.includes('}') && !newsItems.some(item => item.link === link)) {
            newsItems.push({ title, link })
          }
        })
      } catch (error) {
        console.error(`Error fetching page ${page}:`, error)
      }
    }

    let count = 0
    for (const item of newsItems.slice(0, 20)) {
      // Check for duplicate
      const existing = await rawNewsCollection.findOne({ title: item.title })
      if (existing) {
        console.log(`Skipping duplicate: ${item.title}`)
        continue
      }

      try {
        // Fetch article content
        const articleResponse = await fetch(item.link, { headers, signal: AbortSignal.timeout(10000) })
        if (articleResponse.ok) {
          const articleHtml = await articleResponse.text()
          const $article = cheerio.load(articleHtml)
          const contentDiv = $article('.arti-flow, .content_wrapper, #contentdata')
          let content = contentDiv.text().trim().replace(/\s+/g, ' ')
          let summary = content.length > 500 ? content.substring(0, 500) + '...' : content
          if (!content) {
            content = item.title
            summary = item.title
          }

          const newsId = randomUUID()
          const newsDate = new Date()

          await rawNewsCollection.insertOne({
            id: newsId,
            title: item.title,
            content,
            summary,
            source: 'Moneycontrol',
            date: newsDate,
            url: item.link,
            category: 'business',
            tags: ['business', 'finance', 'stocks']
          })
          count++
        } else {
          // Fallback without content
          const newsId = randomUUID()
          const newsDate = new Date()
          await rawNewsCollection.insertOne({
            id: newsId,
            title: item.title,
            content: item.title,
            summary: item.title,
            source: 'Moneycontrol',
            date: newsDate,
            url: item.link,
            category: 'business',
            tags: ['business', 'finance', 'stocks']
          })
          count++
        }
      } catch (error) {
        console.error(`Failed to fetch content for ${item.title}:`, error)
        // Still insert without content
        const newsId = randomUUID()
        const newsDate = new Date()
        await rawNewsCollection.insertOne({
          id: newsId,
          title: item.title,
          content: item.title,
          summary: item.title,
          source: 'Moneycontrol',
          date: newsDate,
          url: item.link,
          category: 'business',
          tags: ['business', 'finance', 'stocks']
        })
        count++
      }
    }

    return NextResponse.json({
      success: true,
      message: `Successfully scraped and processed ${count} news items`
    })
  } catch (error) {
    console.error("Error scraping news:", error)
    return NextResponse.json({ success: false, error: "Failed to scrape news" }, { status: 500 })
  } finally {
    await disconnectFromDatabase()
  }
}
