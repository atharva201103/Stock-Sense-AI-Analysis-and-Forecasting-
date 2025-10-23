import { NextResponse } from "next/server"
import { verifyToken } from "@/lib/auth-utils"
import { exec } from "child_process"
import { promisify } from "util"
import path from "path"

const execAsync = promisify(exec)

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

    // Get the backend directory path
    const backendPath = path.join(process.cwd(), "..", "backend")

    // Run the Django management command with virtual environment
    const { stdout, stderr } = await execAsync(
      "source venv/bin/activate && python manage.py scrape_stock_prices",
      {
        cwd: backendPath,
        timeout: 300000, // 5 minutes timeout
        maxBuffer: 1024 * 1024 * 10, // 10MB buffer
        shell: "/bin/bash" // Use bash to support source command
      }
    )

    console.log("Scrape stock prices stdout:", stdout)
    if (stderr) {
      console.log("Scrape stock prices stderr:", stderr)
    }

    // Parse the output to extract the count
    const countMatch = stdout.match(/Successfully scraped (\d+) stock prices/)
    const count = countMatch ? parseInt(countMatch[1]) : 0

    return NextResponse.json({
      success: true,
      message: `Successfully scraped and processed ${count} stock prices`
    })
  } catch (error) {
    console.error("Error running scrape_stock_prices command:", error)
    return NextResponse.json({
      success: false,
      error: `Failed to scrape stock prices: ${error instanceof Error ? error.message : 'Unknown error'}`
    }, { status: 500 })
  }
}
