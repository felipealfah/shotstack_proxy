import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, Video, Users, Clock, CreditCard, RefreshCw } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/hooks/use-toast";
import { ApiKeyManager } from "@/components/ApiKeyManager";
import { RecentVideos } from "@/components/RecentVideos";
import { useDashboardMetrics } from "@/hooks/useDashboardMetrics";
import type { Session, User } from "@supabase/supabase-js";

const Index = () => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();
  
  // Hook para métricas do dashboard
  const {
    activeRenders,
    completedVideos,
    activeApiKeys,
    averageRenderTime,
    tokenBalance,
    loading: metricsLoading,
    error: metricsError,
    refresh: refreshMetrics
  } = useDashboardMetrics(user);

  useEffect(() => {
    // Set up auth state listener
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        setSession(session);
        setUser(session?.user ?? null);
        setLoading(false);
      }
    );

    // Check for existing session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleSignOut = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) {
      toast({
        title: "Erro",
        description: "Erro ao fazer logout",
        variant: "destructive",
      });
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!user) {
    window.location.href = '/';
    return null;
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold">Aion Videos API Dashboard</h1>
          <div className="flex items-center gap-4">
            <Badge variant="outline">{user.email}</Badge>
            <Button variant="outline" onClick={handleSignOut}>
              Sair
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-8">
          {/* Renders Ativos */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Renders Ativos
              </CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {metricsLoading ? (
                <div className="text-2xl font-bold animate-pulse">--</div>
              ) : (
                <div className="text-2xl font-bold">{activeRenders}</div>
              )}
              <p className="text-xs text-muted-foreground">
                Em processamento
              </p>
            </CardContent>
          </Card>

          {/* Vídeos Prontos */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Vídeos Prontos
              </CardTitle>
              <Video className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {metricsLoading ? (
                <div className="text-2xl font-bold animate-pulse">--</div>
              ) : (
                <div className="text-2xl font-bold">{completedVideos}</div>
              )}
              <p className="text-xs text-muted-foreground">
                Total renderizados
              </p>
            </CardContent>
          </Card>

          {/* API Keys Ativas */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                API Keys Ativas
              </CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {metricsLoading ? (
                <div className="text-2xl font-bold animate-pulse">--</div>
              ) : (
                <div className="text-2xl font-bold">{activeApiKeys}</div>
              )}
              <p className="text-xs text-muted-foreground">
                Limite: 10 chaves
              </p>
            </CardContent>
          </Card>

          {/* Tempo Médio */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Tempo Médio
              </CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {metricsLoading ? (
                <div className="text-2xl font-bold animate-pulse">--</div>
              ) : (
                <div className="text-2xl font-bold">
                  {averageRenderTime > 0 ? `${averageRenderTime}min` : '--'}
                </div>
              )}
              <p className="text-xs text-muted-foreground">
                Por renderização
              </p>
            </CardContent>
          </Card>

          {/* Saldo de Tokens */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                Créditos
              </CardTitle>
              <CreditCard className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {metricsLoading ? (
                <div className="text-2xl font-bold animate-pulse">--</div>
              ) : (
                <div className="text-2xl font-bold">{tokenBalance}</div>
              )}
              <p className="text-xs text-muted-foreground">
                Tokens disponíveis
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Botão de refresh e status de erro */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={refreshMetrics}
              disabled={metricsLoading}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${metricsLoading ? 'animate-spin' : ''}`} />
              Atualizar Métricas
            </Button>
            {metricsError && (
              <Badge variant="destructive" className="text-xs">
                Erro ao carregar dados
              </Badge>
            )}
          </div>
        </div>

        <div className="mb-8">
          <ApiKeyManager />
        </div>

        {/* Recent Videos Section - Full Width Above Documentation */}
        <div className="mb-8">
          <RecentVideos user={user} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Como Usar</CardTitle>
              <CardDescription>
                Integração com n8n para renderização de vídeos
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-muted p-4 rounded-lg">
                <h4 className="font-semibold mb-2">1. Gere sua API Key</h4>
                <p className="text-sm text-muted-foreground">
                  Crie uma API key acima para usar nos seus fluxos do n8n
                </p>
              </div>
              
              <div className="bg-muted p-4 rounded-lg">
                <h4 className="font-semibold mb-2">2. Configure o n8n</h4>
                <p className="text-sm text-muted-foreground">
                  Use a API key no header Authorization: Bearer sua_chave
                </p>
              </div>

              <div className="bg-muted p-4 rounded-lg">
                <h4 className="font-semibold mb-2">3. Endpoint de Renderização</h4>
                <code className="text-sm bg-black text-green-400 p-2 rounded block">
                  POST http://localhost:8002/api/v1/render
                </code>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Documentação</CardTitle>
              <CardDescription>
                Links úteis para integração
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                <h4 className="font-semibold">📖 Rotas da API</h4>
                <p className="text-sm text-muted-foreground">
                  Consulte o arquivo <code>rotas.md</code> na raiz do projeto
                </p>
              </div>
              
              <div className="space-y-2">
                <h4 className="font-semibold">🔧 Swagger UI</h4>
                <code className="text-sm text-blue-600">
                  http://localhost:8002/docs
                </code>
              </div>

              <div className="space-y-2">
                <h4 className="font-semibold">💰 Billing</h4>
                <p className="text-sm text-muted-foreground">
                  Cada renderização consome 1 token
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
};

export default Index;