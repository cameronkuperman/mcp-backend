# Health Story Integration Guide

This guide will walk you through integrating the Health Story feature into your Next.js dashboard.

## Overview

The Health Story feature generates weekly AI-powered narratives about a user's health journey by analyzing:
- Oracle chat conversations
- Quick scan results
- Deep dive analyses
- Medical profile data
- Symptom tracking entries

## Backend Setup (Already Complete)

The MCP server endpoint is ready at:
```
POST https://web-production-945c4.up.railway.app/api/health-story
```

### Request Format:
```json
{
  "user_id": "string",
  "date_range": {
    "start": "ISO date string",
    "end": "ISO date string"
  }
}
```

### Response Format:
```json
{
  "success": true,
  "health_story": {
    "header": "Current Analysis",
    "story_text": "Your health journey continues...",
    "generated_date": "December 15, 2024 • AI-generated analysis",
    "story_id": "uuid"
  }
}
```

## Frontend Integration Steps

### 1. Create Database Table

Run the SQL script in your Supabase SQL Editor:

```sql
-- Copy contents from health_stories_table.sql
```

### 2. Add the Service File

Create `services/healthStoryService.ts` in your Next.js app:

```typescript
// Copy contents from healthstory-service.ts
```

### 3. Add the Component

Create `components/HealthStoryComponent.tsx`:

```tsx
// Copy contents from HealthStoryComponent.tsx
```

### 4. Integrate with Dashboard

In your dashboard component, add:

```tsx
import { HealthStoryComponent } from '@/components/HealthStoryComponent';

export function Dashboard() {
  const [showHealthStory, setShowHealthStory] = useState(false);
  const { user } = useUser(); // Your auth hook

  return (
    <div>
      {/* Your existing dashboard */}
      
      {/* Add button to open Health Story */}
      <button
        onClick={() => setShowHealthStory(true)}
        className="px-4 py-2 bg-purple-600 text-white rounded-lg"
      >
        View Health Story
      </button>

      {/* Health Story Modal */}
      <HealthStoryComponent
        userId={user?.id}
        isOpen={showHealthStory}
        onClose={() => setShowHealthStory(false)}
      />
    </div>
  );
}
```

### 5. Update Supabase Types (Optional)

If using TypeScript with Supabase generated types:

```typescript
// In your types file
export interface Database {
  public: {
    Tables: {
      health_stories: {
        Row: {
          id: string;
          user_id: string;
          header: string;
          story_text: string;
          generated_date: string;
          date_range: { start: string; end: string } | null;
          data_sources: {
            oracle_chats: number;
            quick_scans: number;
            deep_dives: number;
            symptom_entries: number;
          } | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          // Same fields, most optional
        };
        Update: {
          // Same fields, all optional
        };
      };
    };
  };
}
```

## Setting Up Automatic Weekly Generation

Choose one of these options:

### Option 1: Supabase Edge Functions (Recommended)

1. Create edge function following the example in `health-story-cron.ts`
2. Deploy using Supabase CLI
3. Set up pg_cron schedule

### Option 2: Vercel Cron

1. Create API route at `app/api/cron/health-stories/route.ts`
2. Add cron configuration to `vercel.json`
3. Set `CRON_SECRET` in environment variables

### Option 3: Manual Trigger

Add a button in your admin panel to manually generate stories for all users.

## Testing

1. **Test the endpoint directly:**
```bash
curl -X POST https://web-production-945c4.up.railway.app/api/health-story \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-id"
  }'
```

2. **Test in your app:**
   - Open the dashboard
   - Click "View Health Story"
   - It should generate a new story if none exists for the past week

## Customization Options

### 1. Modify the Story Prompt

In the MCP server (`run_oracle.py`), update the `system_prompt` in the health story endpoint to change how stories are generated.

### 2. Change Generation Frequency

Modify the date range logic in `healthStoryService.ts`:
```typescript
// For daily stories
startDate.setDate(startDate.getDate() - 1);

// For monthly stories
startDate.setMonth(startDate.getMonth() - 1);
```

### 3. Add Categories

Extend the request to support different story types:
```typescript
interface HealthStoryRequest {
  user_id: string;
  story_type: 'weekly' | 'monthly' | 'symptom-focused' | 'progress';
  // ...
}
```

### 4. Email Notifications

After generating a story, send an email:
```typescript
// In your cron job
if (result.success) {
  await sendEmail({
    to: user.email,
    subject: 'Your Weekly Health Story is Ready',
    template: 'health-story',
    data: { storyId: result.health_story.story_id }
  });
}
```

## Troubleshooting

### Common Issues:

1. **"Failed to generate health story"**
   - Check if user has any data (chats, scans) in the past week
   - Verify API key is set correctly
   - Check server logs for detailed errors

2. **Stories not saving to database**
   - Ensure health_stories table exists
   - Check RLS policies
   - Verify service role key permissions

3. **Cron job not running**
   - Check cron syntax
   - Verify authentication secrets
   - Check function logs

## Next Steps

1. Add ability for users to add personal notes to stories
2. Implement story sharing features
3. Add data visualization charts
4. Create story templates for different health conditions
5. Add export functionality (PDF, email)

## Support

For issues or questions:
- Check MCP server logs: `run_oracle.py`
- Review browser console for frontend errors
- Ensure all environment variables are set correctly