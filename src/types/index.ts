export interface Document {
  id: number;
  filename: string;
  original_name: string;
  page_count: number | null;
  status: "uploaded" | "processing" | "done" | "error";
  error_message: string | null;
  uploaded_at: string;
  processed_at: string | null;
}

export interface NumberFact {
  value: number | null;
  unit: string;
  context: string;
}

export interface Fact {
  id: number;
  document_id: number;
  claim: string;
  entities: string[] | null;
  numbers: NumberFact[] | null;
  time_period: string | null;
  page_number: number | null;
  source_quote: string | null;
  attributes: Record<string, unknown> | null;
  created_at: string;
  document_filename: string | null;
  document_original_name: string | null;
}

export type RelationshipCategory =
  | "corroboration"
  | "contradiction"
  | "context_explained";

export interface Relationship {
  id: number;
  fact_a_id: number;
  fact_b_id: number;
  category: RelationshipCategory;
  explanation: string;
  similarity_score: number | null;
  created_at: string;
  fact_a: Fact | null;
  fact_b: Fact | null;
}

export interface ProcessingStatus {
  document_id: number;
  status: string;
  message: string;
  facts_extracted: number;
  relationships_found: number;
}
