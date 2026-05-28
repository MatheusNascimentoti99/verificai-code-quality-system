import axios from 'axios';
import apiClient from './apiClient';
import {
  UploadedFile,
  ValidationResult,
  UploadApiResponse,
  SUPPORTED_FILE_TYPES,
  FILE_EXTENSIONS,
  MAX_FILE_SIZE
} from '../types/fileUpload';

class FileUploadService {
  private uploadControllers: Map<string, AbortController> = new Map();

  /**
   * Validate file before upload
   */
  validateFile(file: File): ValidationResult {
    // Check file size
    if (file.size > MAX_FILE_SIZE) {
      return {
        valid: false,
        error: `File size exceeds 50MB limit. Selected file is ${this.formatFileSize(file.size)}`
      };
    }

    // Check file type
    let isValidType = false;

    // Check by MIME type
    if (SUPPORTED_FILE_TYPES.includes(file.type)) {
      isValidType = true;
    }

    // Check by file extension if MIME type is not recognized
    if (!isValidType || file.type === '' || file.type === 'application/octet-stream') {
      const extension = this.getFileExtension(file.name).toLowerCase();
      if (Object.keys(FILE_EXTENSIONS).includes(extension)) {
        isValidType = true;
      }
    }

    if (!isValidType) {
      return {
        valid: false,
        error: `Unsupported file type: ${file.type || 'unknown'}. Supported types: JavaScript, TypeScript, Python, Java, C/C++, JSON, XML, HTML, CSS, Markdown, YAML`
      };
    }

    return { valid: true };
  }

  /**
   * Upload a single file with progress tracking
   */
  async uploadFile(
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<UploadedFile> {
    const fileId = this.generateFileId();
    const controller = new AbortController();
    this.uploadControllers.set(fileId, controller);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('fileId', fileId);
      formData.append('originalName', file.name);
      formData.append('relativePath', (file as any).webkitRelativePath || file.name);

      const response = await apiClient.post<UploadApiResponse>('/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress?.(progress);
          }
        },
        signal: controller.signal,
        timeout: 300000, // 5 minutes timeout
      });

      if (response.data.success && response.data.data) {
        return response.data.data;
      } else {
        throw new Error(response.data.error || 'Upload failed');
      }
    } catch (error) {
      if (axios.isCancel(error)) {
        throw new Error('Upload cancelled');
      }
      throw this.handleError(error);
    } finally {
      this.uploadControllers.delete(fileId);
    }
  }

  /**
   * Upload multiple files in parallel
   */
  async uploadMultipleFiles(
    files: File[],
    onProgress?: (fileId: string, progress: number) => void,
    onComplete?: (file: UploadedFile) => void
  ): Promise<UploadedFile[]> {
    const uploadPromises = files.map(async (file) => {
      try {
        const uploadedFile = await this.uploadFile(file, (progress) => {
          onProgress?.(this.generateFileId(), progress);
        });
        onComplete?.(uploadedFile);
        return uploadedFile;
      } catch (error) {
        console.error(`Failed to upload ${file.name}:`, error);
        throw error;
      }
    });

    return Promise.all(uploadPromises);
  }

  /**
   * Cancel an ongoing upload
   */
  cancelUpload(fileId: string): void {
    const controller = this.uploadControllers.get(fileId);
    if (controller) {
      controller.abort();
      this.uploadControllers.delete(fileId);
    }
  }

  /**
   * Cancel all ongoing uploads
   */
  cancelAllUploads(): void {
    this.uploadControllers.forEach((controller) => controller.abort());
    this.uploadControllers.clear();
  }

  /**
   * Get file status from server
   */
  async getFileStatus(fileId: string): Promise<UploadedFile | null> {
    try {
      const response = await apiClient.get<UploadApiResponse>(`/upload/${fileId}/status`);
      return response.data.data || null;
    } catch (error) {
      console.error('Failed to get file status:', error);
      return null;
    }
  }

  /**
   * Delete uploaded file
   */
  async deleteFile(fileId: string): Promise<boolean> {
    try {
      const response = await apiClient.delete(`/upload/${fileId}`);
      return response.data.success;
    } catch (error) {
      console.error('Failed to delete file:', error);
      return false;
    }
  }

  /**
   * Process files from directory (handle webkitRelativePath)
   */
  processDirectoryFiles(files: FileList): File[] {
    const fileArray = Array.from(files);
    const processedFiles: File[] = [];

    fileArray.forEach((file) => {
      // If file has webkitRelativePath, it's from a directory
      if ((file as any).webkitRelativePath) {
        const relativePath = (file as any).webkitRelativePath;
        const validation = this.validateFile(file);

        if (validation.valid) {
          processedFiles.push(file);
        }
      } else {
        const validation = this.validateFile(file);
        if (validation.valid) {
          processedFiles.push(file);
        }
      }
    });

    return processedFiles;
  }

  /**
   * Generate unique file ID
   */
  private generateFileId(): string {
    return `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get file extension from filename
   */
  private getFileExtension(filename: string): string {
    const lastDotIndex = filename.lastIndexOf('.');
    return lastDotIndex === -1 ? '' : filename.substring(lastDotIndex);
  }

  /**
   * Format file size in human readable format
   */
  private formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * Handle API errors
   */
  private handleError(error: any): Error {
    if (axios.isAxiosError(error)) {
      const message = error.response?.data?.error || error.response?.data?.message || error.message;
      return new Error(message);
    }
    return error;
  }
}

// Export singleton instance
export const fileUploadService = new FileUploadService();
export default FileUploadService;