export type RetrievedDocument = {
  image_path: string;
  short_description: string;
  full_description: string;
  score: number;
  mean_similarity?: number;
};

export type ValidationInfo = {
  total_documents: number;
  validated_count: number;
  outlier_count: number;
  approval_ratio: number;
  mean_similarity_threshold: number;
  passed_validation: boolean;
  mean_similarities: number[];
  total_retrieved?: number;
  total_validated?: number;
  iterations?: number;
  final_count?: number;
  requested_count?: number;
};

export type QueryResponse = {
  query_id: string;
  generated_description: string;
  retrieved_documents: RetrievedDocument[];
  quality_score: number | null;
  quality_approved: boolean;
  message?: string | null;
  validation_info?: ValidationInfo | null;
};






