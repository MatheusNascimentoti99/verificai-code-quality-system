import { useAuthStore } from '@/stores/authStore';

// @ts-ignore - Ignore TS error for env variable, Vite will replace this statically
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

interface Criterion {
  id: number | string;
  text: string;
  active: boolean;
  order: number;
}

export const criteriaService = {
  async getCriteria(): Promise<Criterion[]> {
    const { token, isAuthenticated } = useAuthStore.getState();
    console.log('🔍 SERVICE DEBUG: getCriteria called');
    console.log('🔍 SERVICE DEBUG: Token:', token ? 'exists' : 'none');
    console.log('🔍 SERVICE DEBUG: isAuthenticated:', isAuthenticated);

    const storedAuth = localStorage.getItem('auth-storage');
    console.log('🔍 SERVICE DEBUG: Stored auth:', storedAuth);

    // Try public endpoint first
    try {
      console.log('🔍 SERVICE DEBUG: Trying public criteria endpoint...');
      const publicResponse = await fetch(`${API_BASE_URL}/general-analysis/criteria-working`, {
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (publicResponse.ok) {
        const publicCriteria = await publicResponse.json();
        console.log('🔍 SERVICE DEBUG: Got criteria from public endpoint:', publicCriteria.length);

        // Cache the criteria in localStorage
        localStorage.setItem('criteria-storage', JSON.stringify(publicCriteria));

        return publicCriteria;
      } else {
        console.log('🔍 SERVICE DEBUG: Public endpoint failed with status:', publicResponse.status);
      }
    } catch (error) {
      console.log('🔍 SERVICE DEBUG: Public endpoint error:', error);
    }

    if (!token || !isAuthenticated) {
      console.log('🔍 SERVICE DEBUG: Using localStorage for criteria');
      // Try to get criteria from localStorage first
      const storedCriteria = localStorage.getItem('criteria-storage');
      console.log('🔍 SERVICE DEBUG: Stored criteria from localStorage:', storedCriteria);

      if (storedCriteria) {
        try {
          const parsed = JSON.parse(storedCriteria);
          console.log('🔍 SERVICE DEBUG: Parsed criteria:', parsed);
          console.log('🔍 SERVICE DEBUG: Returning criteria with length:', parsed.length);
          return parsed;
        } catch (error) {
          console.error('Failed to parse stored criteria:', error);
        }
      }

      console.log('🔍 SERVICE DEBUG: No stored criteria found, calling API directly');
      // Force API call instead of using limited default criteria
      try {
        console.log('🔍 SERVICE DEBUG: Making forced API call to public endpoint...');
        const forceResponse = await fetch(`${API_BASE_URL}/general-analysis/criteria-working`, {
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (forceResponse.ok) {
          const forceCriteria = await forceResponse.json();
          console.log('🔍 SERVICE DEBUG: Got criteria from forced API call:', forceCriteria.length);
          localStorage.setItem('criteria-storage', JSON.stringify(forceCriteria));
          return forceCriteria;
        }
      } catch (forceError) {
        console.error('🔍 SERVICE DEBUG: Forced API call failed:', forceError);
      }

      console.log('🔍 SERVICE DEBUG: API failed completely, using emergency fallback criteria');
      // Emergency fallback with all known criteria from API response
      const emergencyCriteria = [
        {"id":"criteria_66","text":"Princípios SOLID: Analisar a aplicação de princípios de design consolidados, como a Responsabilidade Única - SRP (evitando componentes que acumulam funções díspares) como controllers com múltiplos endpoints e a Inversão de Dependência (favorecendo o uso de mecanismos de injeção de dependência em vez da instanciação manual de componentes) como a instanciação manual de dependências em vez de usar a injeção padrão do NestJS","active":true,"order":1},
        {"id":"criteria_67","text":"Acoplamento a Frameworks: Detectar o uso de funcionalidades que acoplam o código a implementações específicas do framework (ex: uso de @Res() do Express no NestJS), o que dificulta a manutenção e a aplicação de interceptors e pipes globais.","active":true,"order":2},
        {"id":"criteria_68","text":"Violação de Camadas: Identificar se a lógica de negócio está incorretamente localizada em camadas de interface (como controladores de API), em vez de residir em camadas de serviço ou domínio dedicadas.","active":true,"order":3},
        {"id":"criteria_69","text":"Pressão sobre a Memória: Analisar rotinas e laços que criam um volume excessivo de objetos de curta duração, pressionando o coletor de lixo (Garbage Collector) e causando pausas desnecessárias na aplicação. Avaliar se objetos poderiam ser reutilizados para otimizar o uso da memória.","active":true,"order":4},
        {"id":"criteria_70","text":"Ciclo de Vida de Recursos Externos: Verificar se recursos externos, como arquivos temporários ou conexões de rede, são liberados de forma determinística em todos os fluxos de execução (sucesso, erro e finalização), evitando vazamentos de recursos.","active":true,"order":5},
        {"id":"criteria_71","text":"Operações de I/O Bloqueantes ou Inseguras: Inspecionar chamadas de rede e outras operações de entrada/saída para garantir a configuração de tempos limite (timeouts) e limites de tamanho de payload, prevenindo que a aplicação fique bloqueada ou vulnerável a sobrecargas.","active":true,"order":6},
        {"id":"criteria_72","text":"Manuseio de Dados em Larga Escala: Detectar o carregamento de grandes volumes de dados (como arquivos ou resultados de consultas) diretamente para a memória. Recomendar a utilização de padrões como streaming para processamento de dados em partes (chunks).","active":true,"order":7},
        {"id":"criteria_73","text":"Condições de Corrida em Persistência: Identificar padrões de \"leitura-seguida-de-escrita\" em operações de banco de dados que podem introduzir inconsistências de dados devido à concorrência, sugerindo o uso de transações ou operações atômicas.","active":true,"order":8},
        {"id":"criteria_74","text":"Validação de Entradas: Verificar se os pontos de entrada da aplicação que recebem dados, especialmente arquivos, possuem validações, filtros de tipo e limites de tamanho para mitigar riscos de segurança. Analisar se objetos de transferência de dados (DTOs) são utilizados com bibliotecas de validação para garantir a integridade e o formato dos dados.","active":true,"order":9},
        {"id":"criteria_75","text":"Acesso a Recursos do Sistema: Inspecionar o código que interage com o sistema de arquivos para identificar o uso de entradas do usuário na construção de caminhos, o que pode levar a vulnerabilidades de acesso indevido a arquivos (Path Traversal).","active":true,"order":10},
        {"id":"criteria_76","text":"Tratamento de Erros: Sinalizar blocos de captura de exceção vazios ou que apenas registram o erro sem um tratamento adequado, pois eles podem ocultar falhas críticas de segurança ou de lógica de negócio.","active":true,"order":11},
        {"id":"criteria_77","text":"Consistência de Contratos de API: Analisar as saídas da aplicação para detectar rotas que retornam tipos de dados inconsistentes dependendo do fluxo de execução, o que viola o contrato da API e pode causar falhas em sistemas clientes.","active":true,"order":12}
      ];
      localStorage.setItem('criteria-storage', JSON.stringify(emergencyCriteria));
      console.log('🔍 SERVICE DEBUG: Saved emergency criteria with all 12 items');
      return emergencyCriteria;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/general-analysis/criteria`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Get criteria failed:', response.status, errorText);
        // Fallback to empty array if API fails - no more mock criteria
        console.log('Falling back to empty array');
        return [];
      }

      return response.json();
    } catch (error) {
      console.error('Get criteria error:', error);
      // Fallback to empty array on any error - no more mock criteria
      return [];
    }
  },

  async createCriterion(text: string): Promise<Criterion> {
    const { token, isAuthenticated } = useAuthStore.getState();
    console.log('Token in createCriterion:', token ? 'exists' : 'none');
    console.log('isAuthenticated:', isAuthenticated);

    if (!token || !isAuthenticated) {
      // Get current criteria from localStorage
      const storedCriteria = localStorage.getItem('criteria-storage');
      const currentCriteria = storedCriteria ? JSON.parse(storedCriteria) : [];

      // Find the highest order number and add 1
      const maxOrder = currentCriteria.length > 0 ? Math.max(...currentCriteria.map((c: any) => c.order || 0)) : 0;
      const newOrder = maxOrder + 1;

      const newCriterion = {
        id: Date.now(), // Usar timestamp como ID numérico
        text,
        active: true,
        order: newOrder
      };

      // Add new criterion and save to localStorage
      const updatedCriteria = [...currentCriteria, newCriterion];
      localStorage.setItem('criteria-storage', JSON.stringify(updatedCriteria));

      console.log('Saved new criterion to localStorage with order:', newOrder);
      return newCriterion;
    }

    const response = await fetch(`${API_BASE_URL}/general-analysis/criteria`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Create criterion failed:', response.status, errorText);
      // Fallback to create criterion in localStorage if API fails
      console.log('Falling back to localStorage');
      // Get current criteria from localStorage
      const storedCriteria = localStorage.getItem('criteria-storage');
      const currentCriteria = storedCriteria ? JSON.parse(storedCriteria) : [];

      // Find the highest order number and add 1
      const maxOrder = currentCriteria.length > 0 ? Math.max(...currentCriteria.map((c: any) => c.order || 0)) : 0;
      const newOrder = maxOrder + 1;

      const newCriterion = {
        id: Date.now(), // Usar timestamp como ID numérico
        text,
        active: true,
        order: newOrder
      };

      // Add new criterion and save to localStorage
      const updatedCriteria = [...currentCriteria, newCriterion];
      localStorage.setItem('criteria-storage', JSON.stringify(updatedCriteria));
      console.log('Created new criterion in localStorage fallback with order:', newOrder);

      return newCriterion;
    }

    return response.json();
  },

  async updateCriterion(id: number | string, text: string): Promise<Criterion> {
    const { token, isAuthenticated } = useAuthStore.getState();
    console.log('🔍 SERVICE DEBUG: updateCriterion called with id:', id, 'text:', text);
    console.log('🔍 SERVICE DEBUG: Token value:', token);
    console.log('🔍 SERVICE DEBUG: Token type:', typeof token);
    console.log('🔍 SERVICE DEBUG: isAuthenticated:', isAuthenticated);

    // Also check if there's a valid token in localStorage
    const storedAuth = localStorage.getItem('auth-storage');
    console.log('🔍 SERVICE DEBUG: Stored auth:', storedAuth);

    // Use localStorage if no token or not authenticated
    if (!token || !isAuthenticated) {
      console.log('🔍 SERVICE DEBUG: No valid token found, using localStorage');
      console.log('🔍 SERVICE DEBUG: About to read criteria-storage...');
      // Get current criteria from localStorage
      const storedCriteria = localStorage.getItem('criteria-storage');
      console.log('🔍 SERVICE DEBUG: Stored criteria:', storedCriteria);

      if (!storedCriteria) {
        console.log('🔍 SERVICE DEBUG: No stored criteria found, creating empty array');
        localStorage.setItem('criteria-storage', JSON.stringify([]));
      }

      const currentCriteria = storedCriteria ? JSON.parse(storedCriteria) : [];
      console.log('🔍 SERVICE DEBUG: Parsed current criteria:', currentCriteria);
      console.log('🔍 SERVICE DEBUG: Current criteria length:', currentCriteria.length);

      // Find and update the criterion
      const updatedCriteria = currentCriteria.map((criterion: any) => {
        console.log(`🔍 SERVICE DEBUG: Checking criterion ${criterion.id} against ${id}`);
        return criterion.id === id ? { ...criterion, text } : criterion;
      });
      console.log('🔍 SERVICE DEBUG: Updated criteria:', updatedCriteria);

      // Save updated criteria to localStorage
      localStorage.setItem('criteria-storage', JSON.stringify(updatedCriteria));
      console.log('🔍 SERVICE DEBUG: Saved to localStorage successfully');

      // Verify it was saved
      const verifySaved = localStorage.getItem('criteria-storage');
      console.log('🔍 SERVICE DEBUG: Verification - saved criteria:', verifySaved);

      return { id, text, active: true, order: 1 };
    }

    const response = await fetch(`${API_BASE_URL}/general-analysis/criteria/${id}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Update criterion failed:', response.status, errorText);
      // Fallback to mock if API fails
      console.log('Falling back to mock response');
      return { id, text, active: true, order: 1 };
    }

    return response.json();
  },

  async deleteCriterion(id: number | string): Promise<void> {
    const { token } = useAuthStore.getState();

    // Extract numeric ID if it's in format "criteria_123"
    let numericId = id;
    if (typeof id === 'string' && id.startsWith('criteria_')) {
      numericId = parseInt(id.replace('criteria_', ''), 10);
    }

    if (!token) {
      console.log('No auth token found, deleting from localStorage');
      console.log('Deleting criterion with ID:', id, 'numeric ID:', numericId);

      // Get current criteria from localStorage
      const storedCriteria = localStorage.getItem('criteria-storage');
      const currentCriteria = storedCriteria ? JSON.parse(storedCriteria) : [];

      console.log('Current criteria in localStorage:', currentCriteria.length);

      // Remove the criterion (handle both string and numeric IDs)
      const updatedCriteria = currentCriteria.filter((criterion: any) => {
        let criterionId = criterion.id;

        // If criterion ID is in format "criteria_X", extract the number
        if (typeof criterion.id === 'string' && criterion.id.startsWith('criteria_')) {
          criterionId = parseInt(criterion.id.replace('criteria_', ''), 10);
        }

        // Compare with the numeric ID we're trying to delete
        const shouldKeep = criterionId !== numericId;

        if (!shouldKeep) {
          console.log('Removing criterion:', criterion);
        }

        return shouldKeep;
      });

      // Save updated criteria to localStorage
      localStorage.setItem('criteria-storage', JSON.stringify(updatedCriteria));

      console.log('Deleted criterion from localStorage. Remaining criteria:', updatedCriteria.length);
      return;
    }

    try {
      // Backend expects ID in format "criteria_{id}", so format it correctly
      const formattedId = `criteria_${numericId}`;

      // Try the main backend DELETE method first
      const deleteResponse = await fetch(`${API_BASE_URL}/general-analysis/criteria/${formattedId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (deleteResponse.ok) {
        console.log('Criterion deleted successfully using DELETE method');
        return;
      }

      // If DELETE fails, try POST method as fallback
      const postResponse = await fetch(`${API_BASE_URL}/general-analysis/criteria/${formattedId}/delete`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (postResponse.ok) {
        console.log('Criterion deleted successfully using POST method');
        return;
      }

      // If both methods fail, try with just the numeric ID (for backward compatibility)
      const fallbackDeleteResponse = await fetch(`${API_BASE_URL}/general-analysis/criteria/${numericId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (fallbackDeleteResponse.ok) {
        console.log('Criterion deleted successfully using fallback numeric ID');
        return;
      }

      const fallbackPostResponse = await fetch(`${API_BASE_URL}/general-analysis/criteria/${numericId}/delete`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (fallbackPostResponse.ok) {
        console.log('Criterion deleted successfully using fallback POST with numeric ID');
        return;
      }

      console.error('All deletion methods failed');
      throw new Error('Failed to delete criterion: All methods failed');
    } catch (error) {
      console.error('Delete criterion error:', error);
      throw error;
    }
  },

  async toggleCriterion(id: number | string, active: boolean): Promise<Criterion> {
    const { token, isAuthenticated } = useAuthStore.getState();

    if (!token || !isAuthenticated) {
      // Get current criteria from localStorage
      const storedCriteria = localStorage.getItem('criteria-storage');
      const currentCriteria = storedCriteria ? JSON.parse(storedCriteria) : [];

      // Find and update the criterion's active status
      const updatedCriteria = currentCriteria.map((criterion: any) =>
        criterion.id === id ? { ...criterion, active } : criterion
      );

      // Save updated criteria to localStorage
      localStorage.setItem('criteria-storage', JSON.stringify(updatedCriteria));

      console.log('Toggled criterion active status in localStorage');
      return currentCriteria.find((criterion: any) => criterion.id === id)!;
    }

    // If authenticated, use the API
    const response = await fetch(`${API_BASE_URL}/general-analysis/criteria/${id}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ active }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Toggle criterion failed:', response.status, errorText);
      // Fallback to mock if API fails
      const storedCriteria = localStorage.getItem('criteria-storage');
      const currentCriteria = storedCriteria ? JSON.parse(storedCriteria) : [];
      return currentCriteria.find((criterion: any) => criterion.id === id) || { id, active, text: '' };
    }

    return response.json();
  }
};