import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabaseClient } from '@/utils/supabase-server'

export async function GET(request: NextRequest) {
  try {
    const supabase = createServerSupabaseClient()
    
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const url = new URL(request.url)
    const period = url.searchParams.get('period') || '30' // days
    const apiKeyId = url.searchParams.get('api_key_id')

    const periodDays = parseInt(period)
    if (isNaN(periodDays) || periodDays < 1) {
      return NextResponse.json({ error: 'Invalid period' }, { status: 400 })
    }

    const startDate = new Date()
    startDate.setDate(startDate.getDate() - periodDays)

    // Build query for render requests
    let query = supabase
      .from('render_requests')
      .select('*')
      .eq('user_id', user.id)
      .gte('created_at', startDate.toISOString())
      .order('created_at', { ascending: false })

    // Filter by API key if specified
    if (apiKeyId) {
      query = query.eq('api_key_id', apiKeyId)
    }

    const { data: renderRequests, error: requestsError } = await query

    if (requestsError) {
      console.error('Error fetching render requests:', requestsError)
      return NextResponse.json({ error: 'Failed to fetch usage data' }, { status: 500 })
    }

    // Calculate usage statistics
    const totalRequests = renderRequests.length
    const successfulRequests = renderRequests.filter(req => req.status === 'completed').length
    const failedRequests = renderRequests.filter(req => req.status === 'failed').length
    const totalTokensConsumed = renderRequests.reduce((sum, req) => sum + (req.tokens_consumed || 0), 0)
    const totalVideoDuration = renderRequests.reduce((sum, req) => sum + (req.video_duration_seconds || 0), 0)

    // Group requests by date for charts
    const requestsByDate: { [key: string]: number } = {}
    const tokensByDate: { [key: string]: number } = {}

    renderRequests.forEach(req => {
      const date = new Date(req.created_at).toISOString().split('T')[0]
      requestsByDate[date] = (requestsByDate[date] || 0) + 1
      tokensByDate[date] = (tokensByDate[date] || 0) + (req.tokens_consumed || 0)
    })

    // Convert to arrays for frontend consumption
    const dailyStats = Object.keys(requestsByDate).sort().map(date => ({
      date,
      requests: requestsByDate[date],
      tokens: tokensByDate[date]
    }))

    // Get rate limiting data
    const { data: rateLimitData, error: rateLimitError } = await supabase
      .from('rate_limit_log')
      .select('*')
      .eq('user_id', user.id)
      .gte('created_at', startDate.toISOString())
      .order('created_at', { ascending: false })
      .limit(100)

    if (rateLimitError) {
      console.error('Error fetching rate limit data:', rateLimitError)
    }

    const rateLimitViolations = rateLimitData?.filter(log => log.exceeded_limit) || []

    return NextResponse.json({
      summary: {
        totalRequests,
        successfulRequests,
        failedRequests,
        successRate: totalRequests > 0 ? (successfulRequests / totalRequests) * 100 : 0,
        totalTokensConsumed,
        totalVideoDuration,
        averageVideoLength: totalRequests > 0 ? totalVideoDuration / totalRequests : 0
      },
      dailyStats,
      rateLimitViolations: rateLimitViolations.length,
      recentRequests: renderRequests.slice(0, 10),
      period: periodDays
    })
  } catch (error) {
    console.error('Unexpected error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}