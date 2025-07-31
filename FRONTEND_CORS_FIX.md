# Frontend CORS Fix Instructions

## Problem
The frontend is sending requests with `credentials: 'include'` but the backend was using wildcard CORS (`*`), which is not allowed when credentials are included. This was causing certain endpoints (like `/api/health-intelligence/status`, `/api/deep-dive/ultra-think`) to fail with CORS errors.

## Backend Changes Made (Updated 2025-01-31)
Updated `/core/middleware.py` to:
- Allow specific origins instead of wildcard
- Set `allow_credentials=True`
- Added comprehensive list of allowed origins:
  - localhost:3000, 3001, 3002 (http and https)
  - Netlify deployment URLs
  - Production domains (healthoracle.ai)
- Added support for custom origins via `CORS_ORIGINS` environment variable

## Frontend Changes Needed

### Option 1: Keep credentials (RECOMMENDED if using authentication)
No changes needed in frontend - the backend now supports credentials properly.

### Option 2: Remove credentials (if not using authentication)
If you don't need authentication/cookies, update your fetch calls:

```typescript
// In useHealthIntelligence.ts or wherever you make API calls
const authenticatedFetch = async (url: string, options: RequestInit = {}) => {
  try {
    const response = await fetch(url, {
      ...options,
      // Remove or set to 'omit' if not using authentication
      credentials: 'omit', // Changed from 'include'
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response;
  } catch (error) {
    console.error('Fetch error:', error);
    throw error;
  }
};
```

## Production Deployment Notes

### Option 1: Use Environment Variable (Recommended)
Set the `CORS_ORIGINS` environment variable in your production environment:
```bash
# In Railway, Heroku, or your deployment platform
CORS_ORIGINS=https://your-custom-domain.com,https://another-domain.com
```

### Option 2: Update Code
The allowed origins list in `core/middleware.py` already includes:
- All localhost ports (3000, 3001, 3002)
- Netlify deployment URLs
- healthoracle.ai domains

If you need additional origins, either:
1. Add them to the `CORS_ORIGINS` environment variable (preferred)
2. Update the `allowed_origins` list in `core/middleware.py`

### Why This Fix Was Needed
- Quick Scan and Deep Dive endpoints worked because they might not have been using credentials
- Health Intelligence endpoints require authentication/credentials
- CORS spec doesn't allow wildcard origins (`*`) when credentials are included
- Each endpoint must now explicitly allow the frontend origin

## Testing
1. Restart your backend server
2. Clear browser cache and cookies
3. Try accessing the health intelligence endpoints again

The CORS errors should now be resolved!