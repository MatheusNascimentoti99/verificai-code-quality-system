import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import { useAuthStore } from '@/stores/authStore';

interface ApiResponse<T = any> {
  data: T;
  message?: string;
  status: number;
}

export const useApi = () => {
  const { token, refreshToken, logout } = useAuthStore();

  const api: AxiosInstance = axios.create({
    // @ts-ignore - Ignore TS error for env variable, Vite will replace this statically
    baseURL: import.meta.env.VITE_API_BASE_URL,
    timeout: 300000, // 5 minutos para permitir análise completa da LLM
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor
  api.interceptors.request.use(
    (config) => {
      if (token) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error: AxiosError) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor
  api.interceptors.response.use(
    (response: AxiosResponse) => {
      return response;
    },
    async (error: AxiosError) => {
      const originalRequest = error.config;

      if (error.response?.status === 401 && originalRequest) {
        try {
          await refreshToken();
          if (token) {
            originalRequest.headers = originalRequest.headers || {};
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          }
        } catch (refreshError) {
          logout();
          return Promise.reject(refreshError);
        }
      }

      if (error.response?.status === 403) {
        console.error('Acesso negado:', error.message);
      }

      if (error.response?.status === 500) {
        console.error('Erro interno do servidor:', error.message);
      }

      return Promise.reject(error);
    }
  );

  const get = async <T = any>(url: string, config?: any): Promise<ApiResponse<T>> => {
    try {
      const response = await api.get<ApiResponse<T>>(url, config);
      return response.data;
    } catch (error) {
      throw handleApiError(error as AxiosError);
    }
  };

  const post = async <T = any>(
    url: string,
    data?: any,
    config?: any
  ): Promise<ApiResponse<T>> => {
    try {
      const response = await api.post<ApiResponse<T>>(url, data, config);
      return response.data;
    } catch (error) {
      throw handleApiError(error as AxiosError);
    }
  };

  const put = async <T = any>(
    url: string,
    data?: any,
    config?: any
  ): Promise<ApiResponse<T>> => {
    try {
      const response = await api.put<ApiResponse<T>>(url, data, config);
      return response.data;
    } catch (error) {
      throw handleApiError(error as AxiosError);
    }
  };

  const del = async <T = any>(url: string, config?: any): Promise<ApiResponse<T>> => {
    try {
      const response = await api.delete<ApiResponse<T>>(url, config);
      return response.data;
    } catch (error) {
      throw handleApiError(error as AxiosError);
    }
  };

  const upload = async <T = any>(
    url: string,
    file: File,
    additionalData?: Record<string, any>,
    onProgress?: (progress: number) => void
  ): Promise<ApiResponse<T>> => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      if (additionalData) {
        Object.entries(additionalData).forEach(([key, value]) => {
          formData.append(key, value as string);
        });
      }

      const response = await api.post<ApiResponse<T>>(url, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent: any) => {
          if (onProgress && progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress(progress);
          }
        },
      });

      return response.data;
    } catch (error) {
      throw handleApiError(error as AxiosError);
    }
  };

  const handleApiError = (error: AxiosError): Error => {
    if (error.response) {
      const errorData = error.response.data as any;
      const message = errorData?.message || errorData?.detail || error.message;
      return new Error(message);
    } else if (error.request) {
      return new Error('Erro de conexão com o servidor');
    } else {
      return new Error('Erro ao processar requisição');
    }
  };

  return {
    get,
    post,
    put,
    del,
    upload,
    api,
  };
};