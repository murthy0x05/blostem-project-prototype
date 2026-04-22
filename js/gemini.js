/* ============================================
   🤖 Gemini Module — via Supabase Edge Function
   ============================================
   
   The Gemini API key lives in Supabase Secrets.
   This module calls the "fd-advisor" Edge Function
   which proxies the request to Gemini.
   ============================================ */

import CONFIG from './config.js';

class GeminiAPI {
  constructor() {
    this.conversationHistory = [];
    this.edgeFunctionUrl = `${CONFIG.SUPABASE_URL}/functions/v1/fd-advisor`;
  }

  /** Clear conversation history */
  clearHistory() {
    this.conversationHistory = [];
  }

  /**
   * Get FD suggestion via the Supabase Edge Function
   * @param {string} userQuery — user's text (in their language)
   * @param {string} languageName — e.g. "Hindi", "Telugu", "English"
   * @returns {Promise<string>} — LLM response text
   */
  async getFDSuggestion(userQuery, languageName = 'English') {
    const requestBody = {
      query: userQuery,
      language: languageName,
      history: this.conversationHistory.slice(-6),
    };

    const response = await fetch(this.edgeFunctionUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${CONFIG.SUPABASE_ANON_KEY}`,
        'apikey': CONFIG.SUPABASE_ANON_KEY,
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData?.error || `Server error: ${response.status}`;

      if (response.status === 429) {
        throw new Error('Rate limit reached. Please wait a moment and try again.');
      }
      throw new Error(message);
    }

    const data = await response.json();
    const responseText = data?.suggestion;

    if (!responseText) {
      throw new Error('No response generated. Please try again.');
    }

    // Save to conversation history
    this.conversationHistory.push({
      role: 'user',
      parts: [{ text: userQuery }]
    });
    this.conversationHistory.push({
      role: 'model',
      parts: [{ text: responseText }]
    });

    return responseText;
  }
}

export default GeminiAPI;
