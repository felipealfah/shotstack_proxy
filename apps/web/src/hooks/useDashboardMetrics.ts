import { useEffect, useState } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';
import type { User } from '@supabase/supabase-js';

interface DashboardMetrics {
  activeRenders: number;
  completedVideos: number;
  activeApiKeys: number;
  averageRenderTime: number; // em minutos
  tokenBalance: number;
}

interface MetricState {
  data: DashboardMetrics;
  loading: boolean;
  error: string | null;
}

export const useDashboardMetrics = (user: User | null) => {
  const [state, setState] = useState<MetricState>({
    data: {
      activeRenders: 0,
      completedVideos: 0,
      activeApiKeys: 0,
      averageRenderTime: 0,
      tokenBalance: 0,
    },
    loading: true,
    error: null,
  });

  const { toast } = useToast();
  
  // Configuration from environment variables
  const defaultTokenBalance = parseInt(import.meta.env.VITE_DEFAULT_TOKEN_BALANCE || '100', 10);
  const avgRenderTimeLimit = parseInt(import.meta.env.VITE_AVG_RENDER_TIME_LIMIT || '10', 10);

  const fetchMetrics = async () => {
    if (!user) {
      setState(prev => ({ ...prev, loading: false }));
      return;
    }

    try {
      setState(prev => ({ ...prev, loading: true, error: null }));

      // Buscar renders ativos (status = 'processing') - with fallback
      let activeRendersCount = 0;
      let completedVideosCount = 0;
      
      try {
        const { count: activeRendersCountResult, error: activeRendersError } = await supabase
          .from('renders')
          .select('id', { count: 'exact', head: true })
          .eq('user_id', user.id)
          .eq('status', 'processing');

        if (activeRendersError && activeRendersError.code !== '42P01') {
          throw activeRendersError;
        }
        activeRendersCount = activeRendersCountResult || 0;

        // Buscar vídeos completos
        const { count: completedVideosCountResult, error: completedError } = await supabase
          .from('renders')
          .select('id', { count: 'exact', head: true })
          .eq('user_id', user.id)
          .eq('status', 'completed');

        if (completedError && completedError.code !== '42P01') {
          throw completedError;
        }
        completedVideosCount = completedVideosCountResult || 0;
      } catch (rendersError: any) {
        // If renders table doesn't exist, use placeholder values
        if (rendersError.code === '42P01') {
          console.warn('Renders table does not exist yet. Using placeholder values.');
          activeRendersCount = 0;
          completedVideosCount = 0;
        } else {
          throw rendersError;
        }
      }

      // Buscar API keys ativas
      const { count: activeApiKeysCount, error: apiKeysError } = await supabase
        .from('api_keys')
        .select('id', { count: 'exact', head: true })
        .eq('user_id', user.id)
        .eq('is_active', true);

      if (apiKeysError) throw apiKeysError;

      // Buscar saldo de tokens - with fallback
      let tokenBalance = 0;
      try {
        const { data: balanceData, error: balanceError } = await supabase
          .from('credit_balance')
          .select('balance')
          .eq('user_id', user.id)
          .single();

        if (balanceError && balanceError.code !== 'PGRST116' && balanceError.code !== '42P01') {
          throw balanceError;
        }
        tokenBalance = balanceData?.balance || 0;
      } catch (balanceError: any) {
        if (balanceError.code === '42P01') {
          console.warn('Credit balance table does not exist yet. Using placeholder value.');
          tokenBalance = defaultTokenBalance; // Configurable default starting balance
        } else {
          throw balanceError;
        }
      }

      // Calcular tempo médio de renderização (apenas se houver renders completos)
      let averageTime = 0;
      if (completedVideosCount > 0) {
        try {
          const { data: renderTimes, error: timeError } = await supabase
            .from('renders')
            .select('created_at, updated_at')
            .eq('user_id', user.id)
            .eq('status', 'completed')
            .not('updated_at', 'is', null)
            .limit(avgRenderTimeLimit); // Últimos N renders para média (configurável)

          if (timeError && timeError.code !== '42P01') {
            throw timeError;
          }

          if (renderTimes && renderTimes.length > 0) {
            const totalMinutes = renderTimes.reduce((acc, render) => {
              const start = new Date(render.created_at);
              const end = new Date(render.updated_at);
              const diffMs = end.getTime() - start.getTime();
              const diffMinutes = diffMs / (1000 * 60);
              return acc + diffMinutes;
            }, 0);
            
            averageTime = Math.round((totalMinutes / renderTimes.length) * 10) / 10;
          }
        } catch (timeError: any) {
          if (timeError.code === '42P01') {
            console.warn('Renders table does not exist for time calculation.');
            averageTime = 0;
          } else {
            throw timeError;
          }
        }
      }

      setState({
        data: {
          activeRenders: activeRendersCount,
          completedVideos: completedVideosCount,
          activeApiKeys: activeApiKeysCount || 0,
          averageRenderTime: averageTime,
          tokenBalance: tokenBalance,
        },
        loading: false,
        error: null,
      });

    } catch (error) {
      console.error('Error fetching dashboard metrics:', error);
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Erro ao carregar métricas',
      }));
      
      toast({
        title: "Erro",
        description: "Não foi possível carregar as métricas do dashboard",
        variant: "destructive",
      });
    }
  };

  // Atualizar métricas quando user muda ou ao montar componente
  useEffect(() => {
    fetchMetrics();
  }, [user?.id]); // fetchMetrics é estável, não precisa ser dependência

  // Função para atualizar manualmente
  const refreshMetrics = () => {
    fetchMetrics();
  };

  return {
    ...state.data,
    loading: state.loading,
    error: state.error,
    refresh: refreshMetrics,
  };
};

// Hooks individuais para casos específicos (opcional)
export const useActiveRenders = (user: User | null) => {
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }

    const fetchActiveRenders = async () => {
      const { count, error } = await supabase
        .from('renders')
        .select('id', { count: 'exact', head: true })
        .eq('user_id', user.id)
        .eq('status', 'processing');

      if (!error) {
        setCount(count || 0);
      }
      setLoading(false);
    };

    fetchActiveRenders();
  }, [user?.id]); // user é estável como dependência

  return { count, loading };
};

export const useTokenBalance = (user: User | null) => {
  const [balance, setBalance] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }

    const fetchBalance = async () => {
      const { data, error } = await supabase
        .from('credit_balance')
        .select('balance')
        .eq('user_id', user.id)
        .single();

      if (!error && data) {
        setBalance(data.balance);
      }
      setLoading(false);
    };

    fetchBalance();
  }, [user?.id]); // user é estável como dependência

  return { balance, loading };
};