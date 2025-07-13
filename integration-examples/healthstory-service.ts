// Health Story Service for Next.js Frontend

const API_URL = process.env.NEXT_PUBLIC_ORACLE_API_URL || 'https://web-production-945c4.up.railway.app';

interface HealthStoryRequest {
  user_id: string;
  date_range?: {
    start: string; // ISO date string
    end: string;   // ISO date string
  };
  include_data?: {
    oracle_chats?: boolean;
    deep_dives?: boolean;
    quick_scans?: boolean;
    medical_profile?: boolean;
  };
}

interface HealthStoryResponse {
  success: boolean;
  health_story?: {
    header: string;
    story_text: string;
    generated_date: string;
    story_id: string;
  };
  error?: string;
  message?: string;
}

interface HealthStoryData {
  id: string;
  user_id: string;
  header: string;
  story_text: string;
  generated_date: string;
  date_range?: {
    start: string;
    end: string;
  };
  data_sources?: {
    oracle_chats: number;
    quick_scans: number;
    deep_dives: number;
    symptom_entries: number;
  };
  created_at: string;
}

export const healthStoryService = {
  async generateHealthStory(
    userId: string,
    dateRange?: { start: string; end: string }
  ): Promise<HealthStoryResponse> {
    try {
      const requestBody: HealthStoryRequest = {
        user_id: userId,
        date_range: dateRange,
        include_data: {
          oracle_chats: true,
          deep_dives: true,
          quick_scans: true,
          medical_profile: true
        }
      };

      const response = await fetch(`${API_URL}/api/health-story`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: HealthStoryResponse = await response.json();
      return data;
    } catch (error) {
      console.error('Error generating health story:', error);
      return {
        success: false,
        error: 'Failed to generate health story',
        message: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  },

  async generateWeeklyHealthStory(userId: string): Promise<HealthStoryResponse> {
    // Helper method to generate story for the past week
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 7);

    return this.generateHealthStory(userId, {
      start: startDate.toISOString(),
      end: endDate.toISOString()
    });
  },

  async getHealthStories(userId: string): Promise<HealthStoryData[]> {
    // This would fetch past health stories from your Supabase database
    // Implementation depends on your Supabase client setup
    try {
      // Example implementation:
      // const { data, error } = await supabase
      //   .from('health_stories')
      //   .select('*')
      //   .eq('user_id', userId)
      //   .order('created_at', { ascending: false });
      
      // if (error) throw error;
      // return data || [];
      
      // For now, return empty array
      return [];
    } catch (error) {
      console.error('Error fetching health stories:', error);
      return [];
    }
  }
};

// Export types for use in components
export type { HealthStoryRequest, HealthStoryResponse, HealthStoryData };