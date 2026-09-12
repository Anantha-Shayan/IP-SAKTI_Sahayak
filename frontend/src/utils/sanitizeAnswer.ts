/**
 * Backend generation/network failures currently surface as raw exception
 * strings (e.g. "LLM generation failed: <urlopen error [Errno -2] Name or
 * service not known>"). These are useful in devtools but unusable in the
 * chat UI or spoken aloud by Baba Ji. This turns them into a short,
 * human-readable notice while preserving the technical detail in the
 * console for debugging.
 */
export function sanitizeAnswer(raw: string): string {
  if (!raw) return raw;

  const isLlmFailure = /LLM generation failed/i.test(raw);
  const isNetworkish = /urlopen error|Errno|Name or service not known|ECONNREFUSED|timed out/i.test(
    raw
  );

  if (isLlmFailure || isNetworkish) {
    console.warn('[Baba Ji] Suppressed raw backend error from UI:', raw);
    return "I couldn't reach the language model to generate an answer right now. The evidence below was still retrieved from the indexed corpus — please try again in a moment.";
  }

  return raw;
}2