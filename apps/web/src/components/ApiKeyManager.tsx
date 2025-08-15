import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Copy, Trash2, Plus, Eye, EyeOff } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';

interface ApiKey {
  id: string;
  name: string;
  key_hash: string;
  last_used_at: string | null;
  created_at: string;
  is_active: boolean;
}

interface GenerateApiKeyResponse {
  id: string;
  api_key: string;
}

export function ApiKeyManager() {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [visibleKeys, setVisibleKeys] = useState<Record<string, boolean>>({});
  const { toast } = useToast();

  useEffect(() => {
    loadApiKeys();
  }, []);

  const loadApiKeys = async () => {
    try {
      // Using any to bypass TypeScript issues with new tables
      const client = supabase as any;
      const { data, error } = await client
        .from('api_keys')
        .select('*')
        .order('created_at', { ascending: false });

      if (error) throw error;
      setApiKeys(data || []);
    } catch (error) {
      toast({
        title: "Erro",
        description: "Erro ao carregar API keys",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const createApiKey = async () => {
    setCreating(true);
    try {
      // Using any to bypass TypeScript issues with new functions
      const client = supabase as any;
      const { data, error } = await client.rpc('generate_api_key', {
        key_name: `API Key ${new Date().toLocaleDateString()}`
      });

      if (error) throw error;

      if (data) {
        // Check if there's an error from the function
        if (data.error) {
          toast({
            title: "Limite atingido",
            description: data.message,
            variant: "destructive",
          });
          return;
        }

        toast({
          title: "Sucesso",
          description: "API Key criada com sucesso!",
        });

        // Show the actual key temporarily
        setVisibleKeys(prev => ({ ...prev, [data.id]: true }));
        
        // Copy to clipboard
        await navigator.clipboard.writeText(data.api_key);
        toast({
          title: "Copiado",
          description: "API Key copiada para a área de transferência",
        });
      }

      await loadApiKeys();
    } catch (error) {
      console.error('Error creating API key:', error);
      toast({
        title: "Erro",
        description: "Erro ao criar API key",
        variant: "destructive",
      });
    } finally {
      setCreating(false);
    }
  };

  const deleteApiKey = async (id: string) => {
    try {
      // Using any to bypass TypeScript issues with new tables
      const client = supabase as any;
      const { error } = await client
        .from('api_keys')
        .delete()
        .eq('id', id);

      if (error) throw error;

      toast({
        title: "Sucesso",
        description: "API Key deletada com sucesso",
      });

      await loadApiKeys();
    } catch (error) {
      console.error('Error deleting API key:', error);
      toast({
        title: "Erro",
        description: "Erro ao deletar API key",
        variant: "destructive",
      });
    }
  };

  const copyApiKey = async (keyHash: string, id: string) => {
    try {
      // For existing keys, we can only copy the hash (since we don't store the actual key)
      await navigator.clipboard.writeText(keyHash);
      toast({
        title: "Copiado",
        description: "API Key copiada para a área de transferência",
      });
    } catch (error) {
      toast({
        title: "Erro",
        description: "Erro ao copiar API key",
        variant: "destructive",
      });
    }
  };

  const toggleKeyVisibility = (id: string) => {
    setVisibleKeys(prev => ({ ...prev, [id]: !prev[id] }));
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>API Keys</CardTitle>
          <CardDescription>Carregando...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const hasReachedLimit = apiKeys.length >= 3;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          API Keys
          <Button 
            onClick={createApiKey} 
            disabled={creating || hasReachedLimit} 
            size="sm"
          >
            <Plus className="h-4 w-4 mr-2" />
            {creating ? "Criando..." : "Nova API Key"}
          </Button>
        </CardTitle>
        <CardDescription>
          Gerencie suas chaves de API para acessar o sistema ({apiKeys.length}/3 chaves criadas)
        </CardDescription>
      </CardHeader>
      <CardContent>
        {hasReachedLimit && (
          <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm text-amber-800">
              <strong>Limite atingido:</strong> Você pode ter no máximo 3 API keys ativas. 
              Delete uma chave existente para criar uma nova.
            </p>
          </div>
        )}
        
        {apiKeys.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            Nenhuma API key encontrada. Crie sua primeira chave!
          </div>
        ) : (
          <div className="space-y-4">
            {apiKeys.map((apiKey) => (
              <div
                key={apiKey.id}
                className="flex items-center justify-between p-4 border rounded-lg"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium">{apiKey.name}</h4>
                    <Badge variant={apiKey.is_active ? "default" : "secondary"}>
                      {apiKey.is_active ? "Ativa" : "Inativa"}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <code className="text-sm bg-muted px-2 py-1 rounded">
                      {visibleKeys[apiKey.id] 
                        ? apiKey.key_hash
                        : "••••••••••••••••••••••••••••••••"
                      }
                    </code>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleKeyVisibility(apiKey.id)}
                    >
                      {visibleKeys[apiKey.id] ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    Criada em: {new Date(apiKey.created_at).toLocaleDateString()}
                    {apiKey.last_used_at && (
                      <span> • Último uso: {new Date(apiKey.last_used_at).toLocaleDateString()}</span>
                    )}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => copyApiKey(apiKey.key_hash, apiKey.id)}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => deleteApiKey(apiKey.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}