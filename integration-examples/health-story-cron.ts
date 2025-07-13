// Weekly Health Story Generation Cron Job
// This can be implemented using various approaches:

// Option 1: Supabase Edge Functions (Recommended)
// Create a new edge function in your Supabase project
// File: supabase/functions/generate-weekly-health-stories/index.ts

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { serve } from 'https://deno.land/std@0.177.0/http/server.ts'

const supabaseUrl = Deno.env.get('SUPABASE_URL')!
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
const oracleApiUrl = Deno.env.get('ORACLE_API_URL') || 'https://web-production-945c4.up.railway.app'

const supabase = createClient(supabaseUrl, supabaseServiceKey)

serve(async (req) => {
  try {
    // Get all active users who haven't received a health story in the last 7 days
    const oneWeekAgo = new Date()
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7)

    // Get users who need health stories
    const { data: users, error: usersError } = await supabase
      .from('profiles') // or your users table
      .select('id')
      .eq('active', true) // Only active users

    if (usersError) throw usersError

    const results = []

    // Generate health stories for each user
    for (const user of users || []) {
      try {
        // Check if user already has a recent health story
        const { data: recentStory } = await supabase
          .from('health_stories')
          .select('id')
          .eq('user_id', user.id)
          .gte('created_at', oneWeekAgo.toISOString())
          .single()

        if (!recentStory) {
          // Generate new health story
          const response = await fetch(`${oracleApiUrl}/api/health-story`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              user_id: user.id,
              date_range: {
                start: oneWeekAgo.toISOString(),
                end: new Date().toISOString()
              }
            })
          })

          const result = await response.json()
          results.push({
            user_id: user.id,
            success: result.success,
            story_id: result.health_story?.story_id
          })
        }
      } catch (error) {
        console.error(`Error generating story for user ${user.id}:`, error)
        results.push({
          user_id: user.id,
          success: false,
          error: error.message
        })
      }
    }

    return new Response(
      JSON.stringify({
        success: true,
        generated: results.filter(r => r.success).length,
        failed: results.filter(r => !r.success).length,
        results
      }),
      { headers: { 'Content-Type': 'application/json' } }
    )
  } catch (error) {
    return new Response(
      JSON.stringify({ success: false, error: error.message }),
      { headers: { 'Content-Type': 'application/json' }, status: 500 }
    )
  }
})

// Then schedule this edge function using Supabase Cron:
// In Supabase Dashboard > Database > Extensions > Enable pg_cron
// Then in SQL Editor:
/*
SELECT cron.schedule(
  'generate-weekly-health-stories',
  '0 9 * * 1', -- Every Monday at 9 AM
  $$
  SELECT
    net.http_post(
      url := 'https://your-project.supabase.co/functions/v1/generate-weekly-health-stories',
      headers := jsonb_build_object(
        'Authorization', 'Bearer ' || 'YOUR_ANON_KEY',
        'Content-Type', 'application/json'
      ),
      body := jsonb_build_object()
    );
  $$
);
*/

// Option 2: Next.js API Route with Vercel Cron
// File: app/api/cron/health-stories/route.ts

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

export async function GET(request: NextRequest) {
  // Verify the request is from Vercel Cron
  const authHeader = request.headers.get('authorization')
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  )

  try {
    // Similar logic as above to generate health stories
    // ... implementation ...

    return NextResponse.json({ success: true })
  } catch (error) {
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}

// Then in vercel.json:
/*
{
  "crons": [{
    "path": "/api/cron/health-stories",
    "schedule": "0 9 * * 1"
  }]
}
*/

// Option 3: GitHub Actions
// File: .github/workflows/generate-health-stories.yml
/*
name: Generate Weekly Health Stories

on:
  schedule:
    - cron: '0 9 * * 1' # Every Monday at 9 AM UTC
  workflow_dispatch: # Allow manual trigger

jobs:
  generate-stories:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Health Story Generation
        run: |
          curl -X POST https://your-api.com/api/health-story/batch \
            -H "Authorization: Bearer ${{ secrets.CRON_SECRET }}" \
            -H "Content-Type: application/json"
*/