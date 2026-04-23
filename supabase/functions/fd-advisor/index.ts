// supabase/functions/fd-advisor/index.ts
// Supabase Edge Function — proxies user queries to Gemini API
// The GEMINI_API_KEY is stored in Supabase Secrets

import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models";
const MODEL = "gemini-2.5-flash";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

/**
 * Build the FD advisor system prompt
 */
function buildSystemPrompt(languageName: string): string {
  return `You are "RichPerson FD Advisor", a friendly and knowledgeable Fixed Deposit (FD) financial advisor specializing in the Indian banking system.

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

Deno.serve(async (req: Request) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const GEMINI_API_KEY = Deno.env.get("GEMINI_API_KEY");
    if (!GEMINI_API_KEY) {
      return new Response(
        JSON.stringify({ error: "GEMINI_API_KEY not configured in Supabase secrets" }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const { query, language, history } = await req.json();

    if (!query || !language) {
      return new Response(
        JSON.stringify({ error: "Missing required fields: query, language" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const systemPrompt = buildSystemPrompt(language);

    // Build conversation contents
    const contents: Array<{ role: string; parts: Array<{ text: string }> }> = [];

    // Add history (last 6 exchanges max from the client)
    if (history && Array.isArray(history)) {
      const recentHistory = history.slice(-6);
      for (const msg of recentHistory) {
        contents.push(msg);
      }
    }

    // Add current user message
    contents.push({
      role: "user",
      parts: [{ text: query }],
    });

    const requestBody = {
      system_instruction: {
        parts: [{ text: systemPrompt }],
      },
      contents,
      generationConfig: {
        temperature: 0.7,
        topP: 0.9,
        topK: 40,
        maxOutputTokens: 512,
      },
      safetySettings: [
        { category: "HARM_CATEGORY_HARASSMENT", threshold: "BLOCK_NONE" },
        { category: "HARM_CATEGORY_HATE_SPEECH", threshold: "BLOCK_NONE" },
        { category: "HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold: "BLOCK_NONE" },
        { category: "HARM_CATEGORY_DANGEROUS_CONTENT", threshold: "BLOCK_NONE" },
      ],
    };

    const PRIMARY_MODEL = "gemini-1.5-flash-latest";
    const FALLBACK_MODEL = "gemini-pro";

    async function fetchFromGemini(model: string) {
      const url = `${GEMINI_API_BASE}/${model}:generateContent?key=${GEMINI_API_KEY}`;
      return await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
    }

    let geminiResponse = await fetchFromGemini(PRIMARY_MODEL);

    // If any error occurs (404, 503, etc), try fallback
    if (!geminiResponse.ok) {
      console.log(`Model ${PRIMARY_MODEL} failed with ${geminiResponse.status}, falling back to ${FALLBACK_MODEL}`);
      geminiResponse = await fetchFromGemini(FALLBACK_MODEL);
    }

    if (!geminiResponse.ok) {
      const errorData = await geminiResponse.json().catch(() => ({}));
      const message = (errorData as Record<string, unknown>)?.error
        ? ((errorData as Record<string, { message?: string }>).error?.message || `Gemini API error: ${geminiResponse.status}`)
        : `Gemini API error: ${geminiResponse.status}`;

      return new Response(
        JSON.stringify({ error: message }),
        { status: geminiResponse.status, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    const data = await geminiResponse.json();
    const responseText = (data as Record<string, unknown[]>)?.candidates?.[0]
      ? ((data as { candidates: Array<{ content: { parts: Array<{ text: string }> } }> }).candidates[0].content?.parts?.[0]?.text)
      : null;

    if (!responseText) {
      return new Response(
        JSON.stringify({ error: "No response generated. Please try again." }),
        { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ suggestion: responseText }),
      { status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  } catch (error) {
    console.error("Edge function error:", error);
    return new Response(
      JSON.stringify({ error: "Internal server error. Please try again." }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
