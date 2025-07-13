// Health Story Component for Next.js Frontend
// Place this file in your Next.js app at: components/HealthStoryComponent.tsx

import React, { useState, useEffect } from 'react';
import { healthStoryService, HealthStoryData } from '@/services/healthStoryService';
import { RefreshCw, Calendar, X } from 'lucide-react';

interface HealthStoryComponentProps {
  userId: string;
  isOpen: boolean;
  onClose: () => void;
}

export const HealthStoryComponent: React.FC<HealthStoryComponentProps> = ({
  userId,
  isOpen,
  onClose
}) => {
  const [currentStory, setCurrentStory] = useState<HealthStoryData | null>(null);
  const [pastStories, setPastStories] = useState<HealthStoryData[]>([]);
  const [selectedStory, setSelectedStory] = useState<HealthStoryData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && userId) {
      loadHealthStories();
    }
  }, [isOpen, userId]);

  const loadHealthStories = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Get past stories from database
      const stories = await healthStoryService.getHealthStories(userId);
      setPastStories(stories);

      // If no recent story (within last 7 days), generate a new one
      const oneWeekAgo = new Date();
      oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);

      const recentStory = stories.find(story => 
        new Date(story.created_at) > oneWeekAgo
      );

      if (!recentStory) {
        await generateNewStory();
      } else {
        setCurrentStory(recentStory);
        setSelectedStory(recentStory);
      }
    } catch (err) {
      setError('Failed to load health stories');
      console.error('Error loading health stories:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const generateNewStory = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await healthStoryService.generateWeeklyHealthStory(userId);

      if (response.success && response.health_story) {
        const newStory: HealthStoryData = {
          id: response.health_story.story_id,
          user_id: userId,
          header: response.health_story.header,
          story_text: response.health_story.story_text,
          generated_date: response.health_story.generated_date,
          created_at: new Date().toISOString()
        };

        setCurrentStory(newStory);
        setSelectedStory(newStory);
        setPastStories([newStory, ...pastStories]);
      } else {
        setError(response.error || 'Failed to generate health story');
      }
    } catch (err) {
      setError('Failed to generate health story');
      console.error('Error generating health story:', err);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-800">
          <h2 className="text-2xl font-semibold text-white">Health Story</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        <div className="flex h-[calc(90vh-88px)]">
          {/* Sidebar - Past Episodes */}
          <div className="w-80 border-r border-gray-800 overflow-y-auto">
            <div className="p-4">
              <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
                Past Episodes
              </h3>
              
              {pastStories.map((story) => (
                <button
                  key={story.id}
                  onClick={() => setSelectedStory(story)}
                  className={`w-full text-left p-4 rounded-lg mb-2 transition-colors ${
                    selectedStory?.id === story.id
                      ? 'bg-purple-900/30 border border-purple-500'
                      : 'bg-gray-800 hover:bg-gray-700 border border-transparent'
                  }`}
                >
                  <div className="text-sm text-gray-400 mb-1">
                    {new Date(story.created_at).toLocaleDateString('en-US', {
                      month: 'long',
                      day: 'numeric',
                      year: 'numeric'
                    })}
                  </div>
                  <div className="text-white font-medium">{story.header}</div>
                  <div className="text-sm text-gray-400 mt-1 line-clamp-2">
                    {story.story_text.substring(0, 100)}...
                  </div>
                </button>
              ))}

              {pastStories.length === 0 && !isLoading && (
                <div className="text-gray-500 text-center py-8">
                  No past stories yet
                </div>
              )}
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <RefreshCw className="animate-spin w-8 h-8 text-purple-500 mx-auto mb-4" />
                  <p className="text-gray-400">Generating your health story...</p>
                </div>
              </div>
            ) : error ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <p className="text-red-400 mb-4">{error}</p>
                  <button
                    onClick={generateNewStory}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            ) : selectedStory ? (
              <div className="p-8">
                <div className="mb-6">
                  <h1 className="text-3xl font-bold text-white mb-2">
                    {selectedStory.header}
                  </h1>
                  <div className="flex items-center text-gray-400 text-sm">
                    <Calendar size={16} className="mr-2" />
                    {selectedStory.generated_date}
                  </div>
                </div>

                <div className="prose prose-invert max-w-none">
                  {selectedStory.story_text.split('\n').map((paragraph, index) => (
                    paragraph.trim() && (
                      <p key={index} className="text-gray-300 leading-relaxed mb-4">
                        {paragraph}
                      </p>
                    )
                  ))}
                </div>

                {selectedStory.data_sources && (
                  <div className="mt-8 p-4 bg-gray-800 rounded-lg">
                    <h3 className="text-sm font-medium text-gray-400 mb-2">Data Sources</h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500">Oracle Chats:</span>{' '}
                        <span className="text-white">{selectedStory.data_sources.oracle_chats}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Quick Scans:</span>{' '}
                        <span className="text-white">{selectedStory.data_sources.quick_scans}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Deep Dives:</span>{' '}
                        <span className="text-white">{selectedStory.data_sources.deep_dives}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Symptom Entries:</span>{' '}
                        <span className="text-white">{selectedStory.data_sources.symptom_entries}</span>
                      </div>
                    </div>
                  </div>
                )}

                <div className="mt-6 flex gap-4">
                  <button className="text-purple-400 hover:text-purple-300 text-sm flex items-center">
                    + Add personal note
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <p className="text-gray-400 mb-4">No story selected</p>
                  <button
                    onClick={generateNewStory}
                    className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                  >
                    Generate New Story
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};