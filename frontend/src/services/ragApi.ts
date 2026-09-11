import type { ArchitectureStateInfo } from '../components/ConversationAnalysisPanel';
import type { Message } from '../components/ConversationAnalysisPanel';

/** Matches backend RAGResponse.to_dict() */
export interface RagQueryResponse {
  answer: string;
  citations: BackendCitation[];
  evidence: BackendEvidenceChunk[];
  confidence: string;
  grounded: boolean;
  retrieval_stats?: {
    bm25_top_k?: number;
    dense_top_k?: number;
    hybrid_candidates?: number;
    reranked_candidates?: number;
  };
}

export interface BackendCitation {
  citation_id?: string;
  chunk_id?: string;
  document_name?: string;
  source_path?: string | null;
  pdf_page_start?: number | null;
  pdf_page_end?: number | null;
  section?: string | null;
  article?: string | null;
  chapter?: string | null;
  rule?: string | null;
  regulation?: string | null;
  document_type?: string | null;
}

export interface BackendEvidenceChunk {
  chunk_id?: string;
  text?: string;
  document_name?: string;
  citation_id?: string;
  section?: string | null;
  article?: string | null;
  page_start?: number | null;
  page_end?: number | null;
}

export class RagApiError extends Error {
  status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = 'RagApiError';
    this.status = status;
  }
}

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? '';

const QUERY_TIMEOUT_MS = 120_000;

function pageLabel(start?: number | null, end?: number | null): string {
  if (start == null) return '';
  if (end != null && end !== start) return `pp. ${start}–${end}`;
  return `p. ${start}`;
}

export function mapCitationsForUi(
  citations: BackendCitation[],
  evidence: BackendEvidenceChunk[]
): NonNullable<Message['citations']> {
  const evidenceByChunk = new Map<string, BackendEvidenceChunk>();
  for (const chunk of evidence) {
    if (chunk.chunk_id) {
      evidenceByChunk.set(chunk.chunk_id, chunk);
    }
  }

  return citations.map((c) => {
    const matched = c.chunk_id ? evidenceByChunk.get(c.chunk_id) : undefined;
    const snippetSource = matched?.text ?? '';
    const snippet =
      snippetSource.length > 280 ? `${snippetSource.slice(0, 277).trim()}…` : snippetSource.trim();

    const sectionParts = [c.section, c.article, c.chapter, c.rule, c.regulation].filter(Boolean);
    const sectionLabel = sectionParts.join(' · ') || '—';

    const authorityParts = [
      c.citation_id,
      pageLabel(c.pdf_page_start, c.pdf_page_end),
      c.source_path ? c.source_path.split('/').pop() : null,
    ].filter(Boolean);

    return {
      title: c.document_name || 'Indexed source',
      authority: authorityParts.join(' · ') || 'Corpus provenance',
      section: sectionLabel,
      snippet: snippet || 'See indexed chunk in corpus.',
    };
  });
}

function confidenceToTier(confidence: string, grounded: boolean): string {
  if (!grounded) return 'Insufficient';
  switch (confidence) {
    case 'high':
      return 'High';
    case 'medium':
      return 'Medium';
    case 'low':
      return 'Low';
    case 'none':
      return 'Insufficient';
    case 'error':
      return 'Error';
    default:
      return grounded ? 'Medium' : 'Insufficient';
  }
}

function confidenceToScore(confidence: string, grounded: boolean): string {
  if (!grounded) return '—';
  if (confidence === 'high') return 'High';
  if (confidence === 'medium') return 'Medium';
  if (confidence === 'low') return 'Low';
  if (confidence === 'dummy') return 'Dev';
  if (confidence === 'error') return '—';
  return confidence || '—';
}

export function mapRagResponseToArchitectureState(response: RagQueryResponse): ArchitectureStateInfo {
  const docNames = [
    ...new Set(
      response.citations
        .map((c) => c.document_name)
        .filter((name): name is string => Boolean(name))
    ),
  ];

  const reranked = response.retrieval_stats?.reranked_candidates;

  return {
    step: response.grounded ? 'complete' : 'validation',
    detectedEntities:
      docNames.length > 0 ? docNames.slice(0, 3) : ['Query processed against indexed corpus'],
    formulationCategory:
      reranked != null
        ? `Hybrid retrieval · ${reranked} evidence chunk(s)`
        : 'Hybrid retrieval (BM25 + dense)',
    legalRegime: 'Indexed IP & traditional-knowledge corpus',
    confidenceScore: confidenceToScore(response.confidence, response.grounded),
    confidenceTier: confidenceToTier(response.confidence, response.grounded),
  };
}

export async function queryRag(query: string): Promise<RagQueryResponse> {
  const trimmed = query.trim();
  if (!trimmed) {
    throw new RagApiError('Please enter a question before submitting.');
  }

  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), QUERY_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE}/api/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: trimmed }),
      signal: controller.signal,
    });

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const errBody = await response.json();
        if (typeof errBody.detail === 'string') {
          detail = errBody.detail;
        } else if (errBody.detail) {
          detail = JSON.stringify(errBody.detail);
        }
      } catch {
        // ignore parse errors
      }
      throw new RagApiError(
        detail || `Request failed (${response.status})`,
        response.status
      );
    }

    const data = (await response.json()) as RagQueryResponse;
    if (typeof data.answer !== 'string') {
      throw new RagApiError('Unexpected response from knowledge service.');
    }
    return data;
  } catch (err) {
    if (err instanceof RagApiError) {
      throw err;
    }
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new RagApiError('The request timed out. Check that the backend and Qdrant are running.');
    }
    throw new RagApiError(
      'Could not reach the knowledge backend. Start the API on port 8000 and try again.'
    );
  } finally {
    window.clearTimeout(timeoutId);
  }
}
