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

1. Update the backend `core/middleware.py` to include your production frontend URL:
   ```python
   allowed_origins = [
       "http://localhost:3000",
       "http://localhost:3001", 
       "https://your-production-frontend.com",  # Add this
       # ... other origins
   ]
   ```

2. Make sure your backend environment variables are set correctly in production.

## Testing
1. Restart your backend server
2. Clear browser cache and cookies
3. Try accessing the health intelligence endpoints again

The CORS errors should now be resolved!