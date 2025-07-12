# Railway Deployment Guide for Oracle AI Server

This guide will help you deploy your Oracle AI server (with Quick Scan and Deep Dive) to Railway.

## Prerequisites

1. Railway account (sign up at https://railway.app)
2. Railway CLI installed (optional but recommended)
3. Git repository for your project

## Step 1: Prepare Your Project

All necessary files are already configured:
- ✅ `requirements.txt` - Python dependencies
- ✅ `Procfile` - Tells Railway how to start your app
- ✅ `runtime.txt` - Specifies Python version
- ✅ `railway.json` - Railway configuration
- ✅ `.env` - Environment variables (not committed to git)

## Step 2: Create Railway Project

### Option A: Using Railway Dashboard (Recommended)

1. Go to https://railway.app and sign in
2. Click "New Project"
3. Choose "Deploy from GitHub repo"
4. Connect your GitHub account and select your repository
5. Railway will automatically detect it's a Python project

### Option B: Using Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize new project
railway init

# Link to existing project (if you created one in dashboard)
railway link
```

## Step 3: Configure Environment Variables

In Railway dashboard:

1. Go to your project
2. Click on your service
3. Go to "Variables" tab
4. Add the following variables:

```bash
# Required Variables
OPENROUTER_API_KEY=your-openrouter-api-key-here
SUPABASE_URL=https://ekaxwbatykostnmopnhn.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_KEY=your-service-key-here

# Optional Variables
PORT=8000  # Railway will override this automatically
APP_URL=https://your-app.railway.app  # Will be set after deployment
```

⚠️ **IMPORTANT**: Replace the Supabase keys with your actual keys from `.env` file

## Step 4: Deploy

### Option A: Automatic Deploy (GitHub Integration)

If you connected GitHub, Railway will automatically deploy when you push to your main branch.

```bash
# Commit your changes
git add .
git commit -m "Ready for Railway deployment"
git push origin main
```

### Option B: Manual Deploy (Railway CLI)

```bash
# Deploy current directory
railway up

# Check deployment logs
railway logs
```

## Step 5: Get Your API URL

After deployment:

1. Go to Railway dashboard
2. Click on your service
3. Go to "Settings" tab
4. Under "Domains", click "Generate Domain"
5. Your API will be available at: `https://your-app-name.railway.app`

## Step 6: Update Your Next.js App

Update your Next.js environment variables:

```env
# .env.local
NEXT_PUBLIC_ORACLE_API_URL=https://your-app-name.railway.app
```

## Step 7: Test Your Endpoints

Test that all endpoints are working:

```bash
# Health check
curl https://your-app-name.railway.app/api/health

# Quick Scan test
curl -X POST https://your-app-name.railway.app/api/quick-scan \
  -H "Content-Type: application/json" \
  -d '{
    "body_part": "head",
    "form_data": {
      "symptoms": "headache"
    }
  }'

# Deep Dive test
curl -X POST https://your-app-name.railway.app/api/deep-dive/start \
  -H "Content-Type: application/json" \
  -d '{
    "body_part": "head",
    "form_data": {
      "symptoms": "severe headache"
    }
  }'
```

## Monitoring & Logs

### View Logs

In Railway dashboard:
- Click on your service
- Go to "Deployments" tab
- Click on any deployment to see logs

Or use CLI:
```bash
railway logs --tail
```

### Monitor Usage

Railway provides:
- CPU and Memory usage graphs
- Request metrics
- Error tracking
- Deployment history

## Troubleshooting

### Common Issues

1. **Port binding error**
   - Railway automatically sets PORT env variable
   - Make sure your app uses `os.environ.get("PORT", 8000)`

2. **Module not found errors**
   - Check that all dependencies are in `requirements.txt`
   - Railway uses the exact versions specified

3. **Environment variable issues**
   - Double-check all variables are set in Railway dashboard
   - Use Railway's "Raw Editor" for bulk editing

4. **CORS errors**
   - Your FastAPI app already has CORS configured for all origins
   - If issues persist, check browser console for specific origin

### Debug Commands

```bash
# Check deployment status
railway status

# View environment variables (hidden values)
railway variables

# Restart service
railway restart

# View recent deployments
railway deployments
```

## Advanced Configuration

### Custom Domain

1. Go to Settings → Domains
2. Add your custom domain
3. Update DNS records as instructed

### Scaling

Railway automatically scales your app. For manual control:
1. Go to Settings → Resource Limits
2. Adjust CPU and Memory limits

### Health Checks

Railway uses your `/api/health` endpoint for health checks automatically.

## Cost Estimation

Railway's free tier includes:
- $5 free credits monthly
- 512MB RAM
- 1 vCPU

Your Oracle AI server should comfortably run within free tier limits for development/testing.

## Next Steps

1. Set up monitoring alerts
2. Configure custom domain (optional)
3. Set up CI/CD with GitHub Actions (optional)
4. Monitor usage and optimize as needed

Your Oracle AI server with Quick Scan and Deep Dive is now live! 🎉

## Support

- Railway Discord: https://discord.gg/railway
- Railway Docs: https://docs.railway.app
- Status Page: https://status.railway.app