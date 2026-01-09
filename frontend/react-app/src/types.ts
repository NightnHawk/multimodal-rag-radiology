export type RetrievedDocument = {
  image_path: string;
  short_description: string;
  full_description: string;
  score: number;
};

export type QueryResponse = {
  query_id: string;
  generated_description: string;
  retrieved_documents: RetrievedDocument[];
  quality_score: number | null;
  quality_approved: boolean;
  message?: string | null;
};





