/**
 * Service for managing interview settings
 * Provides methods to get and set global interview settings like default topic
 */
export class InterviewSettingsService {
  /**
   * Get the default interview topic from the server
   */
  static async getDefaultTopic(): Promise<string> {
    try {
      const response = await fetch('/api/admin/settings');
      
      if (!response.ok) {
        console.warn('Failed to fetch interview settings, using default topic');
        return 'climate change';
      }
      
      const data = await response.json();
      
      if (data.success && data.settings && data.settings.defaultTopic) {
        return data.settings.defaultTopic;
      }
      
      return 'climate change';
    } catch (error) {
      console.error('Error fetching interview settings:', error);
      return 'climate change';
    }
  }
} 