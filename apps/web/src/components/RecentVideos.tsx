import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { VideoIcon, ExternalLinkIcon, ClockIcon, CheckCircleIcon, XCircleIcon } from 'lucide-react';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';
import type { User } from '@supabase/supabase-js';

interface Video {
  id: string;
  job_id: string;
  project_name: string;
  video_url: string | null;
  status: 'pending' | 'queued' | 'processing' | 'completed' | 'failed';
  created_at: string;
  updated_at: string;
  expires_at: string | null;
  is_expired: boolean;
  duration_seconds?: number;
  shotstack_render_id?: string;
  expires_in_hours?: number;
}

interface RecentVideosProps {
  user: User | null;
}

export const RecentVideos = ({ user }: RecentVideosProps) => {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();
  
  // Configuration from environment variables
  const retentionHours = parseInt(import.meta.env.VITE_VIDEO_RETENTION_HOURS || '48', 10);
  const recentVideosLimit = parseInt(import.meta.env.VITE_RECENT_VIDEOS_LIMIT || '10', 10);

  const fetchRecentVideos = async () => {
    if (!user) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Fetch recent completed and non-expired renders
      const sevenDaysAgo = new Date();
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
      
      const { data, error: fetchError } = await supabase
        .from('renders')
        .select('id, job_id, project_name, video_url, status, created_at, updated_at, expires_at, is_expired, duration_seconds, shotstack_render_id')
        .eq('user_id', user.id)
        .eq('status', 'completed') // Only successful renders
        .eq('is_expired', false) // Only non-expired videos
        .gte('created_at', sevenDaysAgo.toISOString()) // Last 7 days
        .order('created_at', { ascending: false })
        .limit(recentVideosLimit);


      if (fetchError) {
        // If table doesn't exist, show placeholder
        if (fetchError.code === '42P01') {
          setError('Tabela de renders ainda não foi criada. Execute a migração do banco de dados.');
          setVideos([]);
          return;
        }
        throw fetchError;
      }

      // Calculate expiration status for each video using configurable retention policy
      const videosWithExpiration = data?.map((video: any) => {
        let hoursRemaining = 0;
        let isExpired = video.is_expired || false;

        if (video.expires_at && !isExpired) {
          const expiresAt = new Date(video.expires_at);
          const now = new Date();
          const msRemaining = expiresAt.getTime() - now.getTime();
          hoursRemaining = Math.max(0, msRemaining / (1000 * 60 * 60));
        } else if (!video.expires_at) {
          // Fallback calculation for records without expires_at
          const createdAt = new Date(video.created_at);
          const now = new Date();
          const hoursElapsed = (now.getTime() - createdAt.getTime()) / (1000 * 60 * 60);
          hoursRemaining = Math.max(0, retentionHours - hoursElapsed); // Configurable retention period
          isExpired = hoursRemaining <= 0;
        }

        return {
          ...video,
          expires_in_hours: Math.round(hoursRemaining * 10) / 10,
          is_expired: isExpired
        };
      }) || [];

      setVideos(videosWithExpiration);

    } catch (err) {
      console.error('Error fetching recent videos:', err);
      const errorMessage = err instanceof Error ? err.message : 'Erro ao carregar vídeos recentes';
      setError(errorMessage);
      
      toast({
        title: "Erro",
        description: "Não foi possível carregar os vídeos recentes",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecentVideos();
  }, [user?.id]);

  const getStatusBadge = (status: Video['status']) => {
    const statusConfig = {
      pending: { variant: 'secondary' as const, icon: ClockIcon, text: 'Pendente' },
      queued: { variant: 'secondary' as const, icon: ClockIcon, text: 'Na Fila' },
      processing: { variant: 'default' as const, icon: ClockIcon, text: 'Processando' },
      completed: { variant: 'default' as const, icon: CheckCircleIcon, text: 'Concluído' },
      failed: { variant: 'destructive' as const, icon: XCircleIcon, text: 'Falhou' }
    };

    const config = statusConfig[status];
    const Icon = config.icon;

    return (
      <Badge variant={config.variant} className="flex items-center gap-1">
        <Icon className="h-3 w-3" />
        {config.text}
      </Badge>
    );
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMinutes / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffDays > 0) return `${diffDays}d atrás`;
    if (diffHours > 0) return `${diffHours}h atrás`;
    if (diffMinutes > 0) return `${diffMinutes}min atrás`;
    return 'Agora mesmo';
  };

  const getExpirationBadge = (video: Video) => {
    if (video.is_expired) {
      return <Badge variant="destructive">Expirado</Badge>;
    }
    
    const expiresInHours = video.expires_in_hours;
    if (!expiresInHours || expiresInHours <= 0) {
      return <Badge variant="destructive">Expirado</Badge>;
    }

    // Color coding for configurable lifecycle
    if (expiresInHours <= 6) {
      return <Badge variant="destructive">Expira em {Math.floor(expiresInHours)}h</Badge>;
    } else if (expiresInHours <= 24) {
      return <Badge variant="secondary">Expira em {Math.floor(expiresInHours)}h</Badge>;
    } else if (expiresInHours <= retentionHours) {
      const hoursLeft = Math.floor(expiresInHours);
      const daysLeft = Math.floor(hoursLeft / 24);
      const remainingHours = hoursLeft % 24;
      
      if (daysLeft > 0) {
        return <Badge variant="outline">
          {daysLeft}d {remainingHours}h restantes
        </Badge>;
      } else {
        return <Badge variant="outline">{hoursLeft}h restantes</Badge>;
      }
    }
    
    return <Badge variant="outline">Disponível</Badge>;
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <VideoIcon className="h-5 w-5" />
            Vídeos Recentes
          </CardTitle>
          <CardDescription>
            Seus últimos vídeos concluídos com sucesso
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="flex items-center justify-between">
                  <div className="space-y-2">
                    <div className="h-4 bg-muted rounded w-32"></div>
                    <div className="h-3 bg-muted rounded w-24"></div>
                  </div>
                  <div className="h-6 bg-muted rounded w-16"></div>
                </div>
                {i < 2 && <Separator className="mt-4" />}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <VideoIcon className="h-5 w-5" />
            Vídeos Recentes
          </CardTitle>
          <CardDescription>
            Seus últimos vídeos concluídos com sucesso
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <XCircleIcon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-sm text-muted-foreground mb-4">{error}</p>
            <Button onClick={fetchRecentVideos} variant="outline" size="sm">
              Tentar Novamente
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (videos.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <VideoIcon className="h-5 w-5" />
            Vídeos Recentes
          </CardTitle>
          <CardDescription>
            Seus últimos vídeos concluídos com sucesso
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <VideoIcon className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-sm text-muted-foreground mb-2">
              Nenhum vídeo concluído encontrado
            </p>
            <p className="text-xs text-muted-foreground">
              Apenas vídeos renderizados com sucesso aparecerão aqui
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <VideoIcon className="h-5 w-5" />
          Vídeos Recentes
        </CardTitle>
        <CardDescription>
          Seus últimos vídeos concluídos com sucesso
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Scrollable container - max 8 videos visible (approx 480px height) */}
        <div className="max-h-[480px] overflow-y-auto border border-gray-100 rounded-md" style={{
          scrollbarWidth: 'thin',
          scrollbarColor: '#d1d5db #f3f4f6'
        }}>
          <div className="space-y-4 pr-2">
            {videos.map((video, index) => (
              <div key={video.id}>
                <div className="flex items-start justify-between space-x-4">
                  <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="text-sm font-medium truncate">
                      {video.project_name || 'Projeto Sem Nome'}
                    </h4>
                    {getStatusBadge(video.status)}
                  </div>
                  
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span>{formatTimeAgo(video.created_at)}</span>
                    {video.duration_seconds && (
                      <span>{video.duration_seconds}s</span>
                    )}
                    {video.job_id && (
                      <code className="bg-muted px-1 rounded text-xs">
                        {video.job_id.split('-')[0]}...
                      </code>
                    )}
                  </div>
                  
                  {/* Expiration info for completed videos */}
                  {video.status === 'completed' && (
                    <div className="mt-2">
                      {getExpirationBadge(video)}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {video.video_url && !video.is_expired ? (
                    <Button
                      size="sm"
                      variant="outline"
                      asChild
                    >
                      <a
                        href={video.video_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1"
                      >
                        <ExternalLinkIcon className="h-3 w-3" />
                        Ver Vídeo
                      </a>
                    </Button>
                  ) : (
                    <div className="text-sm text-muted-foreground">
                      {video.is_expired ? 'Vídeo expirado' : 'Aguardando transferência...'}
                    </div>
                  )}
                </div>
              </div>
              
              {index < videos.length - 1 && <Separator className="mt-4" />}
            </div>
          ))}
          </div>
        </div>

        {/* Refresh button */}
        <div className="flex justify-center mt-4 pt-4 border-t">
          <Button
            onClick={fetchRecentVideos}
            variant="ghost"
            size="sm"
            disabled={loading}
          >
            Atualizar
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default RecentVideos;