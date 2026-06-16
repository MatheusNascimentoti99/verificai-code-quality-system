/**
 * Frontend service for Architectural Analysis endpoints.
 * Follows the same pattern as analysisService.ts.
 */

import apiClient from './apiClient';

const BASE = '/architectural-analysis';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ArchitecturalDoc {
  id: number;
  user_id: number;
  title: string;
  sharepoint_url?: string;
  content: string;
  file_name?: string;
  content_type?: string;
}

export interface ArchitecturalCriteria {
  id: string;       // "arch_criteria_{n}"
  text: string;
  active: boolean;
  order: number;
}

export interface ArchitecturalAnalyzeRequest {
  analysis_name?: string;
  doc_id: number;
  criteria_ids: string[];
  file_paths?: string[];
  use_code_entry?: boolean;
  code_entry_id?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface ArchitecturalCriterionResult {
  name: string;
  content: string;
}

export interface ArchitecturalAnalysisResult {
  id: number;
  analysis_name: string;
  overall_status: string | null;
  criteria_count: number;
  criteria_results: Record<string, ArchitecturalCriterionResult>;
  raw_response: string;
  model_used?: string;
  usage?: Record<string, number>;
  file_paths: string[];
  processing_time?: string;
  doc_id?: number;
  created_at?: string;
}

// ---------------------------------------------------------------------------
// Service
// ---------------------------------------------------------------------------

export const architecturalAnalysisService = {
  // ---- Docs ---------------------------------------------------------------

  createDoc: async (data: {
    title: string;
    sharepoint_url?: string;
    content: string;
    content_type?: string;
  }): Promise<ArchitecturalDoc> => {
    const response = await apiClient.post(`${BASE}/docs`, data);
    return response.data;
  },

  uploadDoc: async (
    title: string,
    file: File,
    sharepointUrl?: string,
  ): Promise<ArchitecturalDoc> => {
    const formData = new FormData();
    formData.append('title', title);
    formData.append('file', file);
    if (sharepointUrl) formData.append('sharepoint_url', sharepointUrl);

    const response = await apiClient.post(`${BASE}/docs/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  listDocs: async (): Promise<ArchitecturalDoc[]> => {
    const response = await apiClient.get(`${BASE}/docs`);
    return response.data;
  },

  getDoc: async (docId: number): Promise<ArchitecturalDoc> => {
    const response = await apiClient.get(`${BASE}/docs/${docId}`);
    return response.data;
  },

  updateDoc: async (
    docId: number,
    data: Partial<{ title: string; sharepoint_url: string; content: string; content_type: string }>,
  ): Promise<ArchitecturalDoc> => {
    const response = await apiClient.put(`${BASE}/docs/${docId}`, data);
    return response.data;
  },

  deleteDoc: async (docId: number): Promise<void> => {
    await apiClient.delete(`${BASE}/docs/${docId}`);
  },

  // ---- Criteria -----------------------------------------------------------

  listCriteria: async (): Promise<ArchitecturalCriteria[]> => {
    const response = await apiClient.get(`${BASE}/criteria`);
    return response.data;
  },

  createCriterion: async (text: string): Promise<ArchitecturalCriteria> => {
    const response = await apiClient.post(`${BASE}/criteria`, { text });
    return response.data;
  },

  updateCriterion: async (id: string, text: string): Promise<ArchitecturalCriteria> => {
    const response = await apiClient.put(`${BASE}/criteria/${id}`, { text });
    return response.data;
  },

  deleteCriterion: async (id: string): Promise<void> => {
    await apiClient.delete(`${BASE}/criteria/${id}`);
  },

  // ---- Analysis -----------------------------------------------------------

  runAnalysis: async (request: ArchitecturalAnalyzeRequest): Promise<ArchitecturalAnalysisResult> => {
    const response = await apiClient.post(`${BASE}/analyze`, request);
    return response.data;
  },

  // ---- Results ------------------------------------------------------------

  listResults: async (): Promise<ArchitecturalAnalysisResult[]> => {
    const response = await apiClient.get(`${BASE}/results`);
    return response.data;
  },

  getResult: async (resultId: number): Promise<ArchitecturalAnalysisResult> => {
    const response = await apiClient.get(`${BASE}/results/${resultId}`);
    return response.data;
  },

  deleteResult: async (resultId: number): Promise<void> => {
    await apiClient.delete(`${BASE}/results/${resultId}`);
  },
};
