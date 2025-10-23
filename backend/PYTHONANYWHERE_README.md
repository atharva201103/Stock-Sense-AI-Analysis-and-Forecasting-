# PythonAnywhere Deployment Guide

This guide will help you deploy your Django backend to PythonAnywhere for running scheduled scraping tasks.

## Prerequisites

1. **PythonAnywhere Account**: Sign up at [pythonanywhere.com](https://pythonanywhere.com)
2. **MongoDB Atlas Account**: Set up a free cluster at [mongodb.com/atlas](https://mongodb.com/atlas)
3. **Git Repository**: Your code should be in a Git repository

## Step 1: Set Up PythonAnywhere

### 1.1 Create a Web App
1. Go to the **Web** tab in your PythonAnywhere dashboard
2. Click **Add a new web app**
3. Choose **Manual configuration** (or **Django** if you want to host the full app)
4. Select Python version (3.10 or later recommended)

### 1.2 Upload Your Code
```bash
# Clone your repository
git clone https://github.com/yourusername/your-repo.git
cd your-repo/backend
```

### 1.3 Set Up Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Install requirements
source venv/bin/activate
pip install -r requirements.txt
```

### 1.4 Run Setup Script
```bash
python setup_pythonanywhere.py
```

## Step 2: Configure Environment Variables

### 2.1 In PythonAnywhere Dashboard
Go to **Variables** section and add:

```
DEBUG=False
SECRET_KEY=your-very-long-random-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/trada_db?retryWrites=true&w=majority
OPENAI_API_KEY=your-openai-api-key-here
```

### 2.2 Or Create .env File
```bash
# Create .env file in your project root
cp .env.example .env
# Edit .env with your actual values
nano .env
```

## Step 3: Set Up Scheduled Tasks

### 3.1 Go to Tasks Tab
In PythonAnywhere dashboard, go to the **Tasks** tab.

### 3.2 Add News Scraping Task
- **Command**: `cd /home/yourusername/your-repo/backend && source venv/bin/activate && python manage.py scrape_news`
- **Schedule**: Every 30 minutes
- **Description**: Scrape financial news from Moneycontrol

### 3.3 Add Stock Price Scraping Task
- **Command**: `cd /home/yourusername/your-repo/backend && source venv/bin/activate && python manage.py scrape_stock_prices`
- **Schedule**: Every 5 minutes
- **Description**: Scrape real-time stock prices

## Step 4: Test Your Commands

### 4.1 Test News Scraping
```bash
cd /home/yourusername/your-repo/backend
source venv/bin/activate
python manage.py scrape_news --verbosity=1
```

### 4.2 Test Stock Price Scraping
```bash
cd /home/yourusername/your-repo/backend
source venv/bin/activate
python manage.py scrape_stock_prices --verbosity=1
```

## Step 5: Monitor and Troubleshoot

### 5.1 Check Logs
- Go to **Web** tab → **Logs** to see any errors
- Check **Tasks** tab → **Task logs** for scheduled task output

### 5.2 Common Issues

**MongoDB Connection Issues:**
- Ensure your MongoDB Atlas IP whitelist includes `0.0.0.0/0` (all IPs)
- Check your connection string format

**Missing Dependencies:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Permission Issues:**
- Make sure your files have proper permissions: `chmod +x manage.py`

**CPU Time Limits:**
- Free tier has 100 seconds/day CPU time
- Upgrade to paid plan for more resources

## Step 6: Update Frontend (Optional)

If you want your frontend to connect to the PythonAnywhere-hosted backend:

1. Update your frontend's API base URL to point to your PythonAnywhere domain
2. Ensure CORS settings allow your frontend domain

## File Structure After Setup

```
/home/yourusername/
├── your-repo/
│   ├── backend/
│   │   ├── venv/                    # Virtual environment
│   │   ├── manage.py               # Django management script
│   │   ├── requirements.txt        # Python dependencies
│   │   ├── .env                    # Environment variables
│   │   ├── setup_pythonanywhere.py # Setup script
│   │   └── aut/                    # Your Django app
│   └── frontend/                   # Your Next.js frontend
```

## Monitoring Your Tasks

- Check the **Tasks** tab regularly to ensure tasks are running
- Monitor your MongoDB Atlas dashboard for data updates
- Set up alerts if needed for task failures

## Cost Considerations

- **Free Tier**: Limited CPU time, suitable for light scraping
- **Paid Plans**: More CPU time and resources for heavier workloads
- **MongoDB Atlas**: Free tier allows 512MB storage

## Security Notes

- Never commit `.env` files to version control
- Use strong, unique passwords for all services
- Regularly rotate API keys and database credentials
- Keep dependencies updated for security patches
