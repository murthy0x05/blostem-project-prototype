/* ============================================
   🤖 Gemini API Module — FD Advisor LLM
   ============================================ */

const GEMINI_API_BASE = 'https://generativelanguage.googleapis.com/v1beta/models';
const MODEL = 'gemini-2.5-flash';

/**
 * Build the system prompt that turns Gemini into an FD advisor
 * @param {string} languageName — e.g. "Hindi", "Telugu"
 */
function buildSystemPrompt(languageName) {
  return `You are "BloStem FD Advisor", a friendly and knowledgeable Fixed Deposit (FD) financial advisor specializing in the Indian banking system.

YOUR CAPABILITIES:
• You know current approximate FD interest rates for major Indian banks (SBI, HDFC Bank, ICICI Bank, Axis Bank, Bank of Baroda, PNB, Kotak Mahindra, IDBI, Post Office, etc.)
• You understand FD types: Regular FD, Tax-Saver FD (5-year lock-in under Section 80C), Flexi FD, Cumulative vs Non-Cumulative, Senior Citizen FD.
• You know Indian tax implications: TDS on interest above ₹40,000 (₹50,000 for senior citizens), Section 80C benefits, taxation of interest income.
• You can recommend tenures, compare banks, explain premature withdrawal penalties, and suggest the best FD strategies based on user goals.

RULES:
1. ALWAYS respond in ${languageName}. The user is speaking in ${languageName}, so reply in that same language.
2. Keep responses concise but helpful — aim for 3-6 sentences unless the user asks for detailed comparison.
3. Use approximate current rates (2025-2026 range). If unsure of exact rates, mention they should verify with the bank.
4. Be warm, professional, and reassuring — many users may be first-time investors.
5. If the user asks something outside of FD/banking, politely redirect them to FD-related topics.
6. Use the Indian number system (lakhs, crores) and ₹ symbol for amounts.
7. Do NOT use markdown formatting — respond in plain text since your response will be read aloud.`;
}

class GeminiAPI {
  constructor() {
    this.apiKey = '';
    this.conversationHistory = [];
  }

  /** Set API key */
  setApiKey(key) {
    this.apiKey = key.trim();
  }

  /** Check if API key is set */
  hasApiKey() {
    return this.apiKey.length > 0;
  }

  /** Clear conversation history */
  clearHistory() {
    this.conversationHistory = [];
  }

  /**
   * Get FD suggestion from Gemini
   * @param {string} userQuery — user's text (in their language)
   * @param {string} languageName — e.g. "Hindi", "Telugu", "English"
   * @returns {Promise<string>} — LLM response text
   */
  async getFDSuggestion(userQuery, languageName = 'English') {
    if (!this.hasApiKey()) {
      throw new Error('API key not configured. Please set your Gemini API key in Settings.');
    }

    const systemPrompt = buildSystemPrompt(languageName);

    // Build conversation contents
    const contents = [];

    // Add history (last 6 exchanges max)
    const recentHistory = this.conversationHistory.slice(-6);
    for (const msg of recentHistory) {
      contents.push(msg);
    }

    // Add current user message
    contents.push({
      role: 'user',
      parts: [{ text: userQuery }]
    });

    const requestBody = {
      system_instruction: {
        parts: [{ text: systemPrompt }]
      },
      contents: contents,
      generationConfig: {
        temperature: 0.7,
        topP: 0.9,
        topK: 40,
        maxOutputTokens: 512,
      },
      safetySettings: [
        { category: 'HARM_CATEGORY_HARASSMENT', threshold: 'BLOCK_NONE' },
        { category: 'HARM_CATEGORY_HATE_SPEECH', threshold: 'BLOCK_NONE' },
        { category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold: 'BLOCK_NONE' },
        { category: 'HARM_CATEGORY_DANGEROUS_CONTENT', threshold: 'BLOCK_NONE' },
      ]
    };

    const url = `${GEMINI_API_BASE}/${MODEL}:generateContent?key=${this.apiKey}`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData?.error?.message || `API error: ${response.status}`;

      if (response.status === 400) {
        throw new Error('Invalid API key. Please check your Gemini API key in Settings.');
      }
      if (response.status === 429) {
        throw new Error('Rate limit reached. Please wait a moment and try again.');
      }
      throw new Error(message);
    }

    const data = await response.json();

    // Extract text from response
    const responseText = data?.candidates?.[0]?.content?.parts?.[0]?.text;

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
