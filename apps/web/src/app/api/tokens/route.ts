import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabaseClient } from '@/utils/supabase-server'

export async function GET() {
  try {
    const supabase = createServerSupabaseClient()
    
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Get user's current token balance
    const { data: userData, error: userError } = await supabase
      .from('users')
      .select('token_balance')
      .eq('id', user.id)
      .single()

    if (userError) {
      console.error('Error fetching user data:', userError)
      return NextResponse.json({ error: 'Failed to fetch token balance' }, { status: 500 })
    }

    // Get recent token transactions
    const { data: transactions, error: transactionsError } = await supabase
      .from('token_transactions')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })
      .limit(50)

    if (transactionsError) {
      console.error('Error fetching transactions:', transactionsError)
      return NextResponse.json({ error: 'Failed to fetch transactions' }, { status: 500 })
    }

    return NextResponse.json({
      balance: userData.token_balance || 0,
      transactions: transactions || []
    })
  } catch (error) {
    console.error('Unexpected error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const supabase = createServerSupabaseClient()
    
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { amount, type, description } = body

    if (!amount || amount <= 0) {
      return NextResponse.json({ error: 'Invalid amount' }, { status: 400 })
    }

    if (!type || !['purchase', 'consumption', 'refund'].includes(type)) {
      return NextResponse.json({ error: 'Invalid transaction type' }, { status: 400 })
    }

    // Start a transaction
    const { data: currentUser, error: fetchError } = await supabase
      .from('users')
      .select('token_balance')
      .eq('id', user.id)
      .single()

    if (fetchError) {
      console.error('Error fetching current balance:', fetchError)
      return NextResponse.json({ error: 'Failed to fetch current balance' }, { status: 500 })
    }

    const currentBalance = currentUser.token_balance || 0
    let newBalance = currentBalance

    // Calculate new balance based on transaction type
    switch (type) {
      case 'purchase':
      case 'refund':
        newBalance = currentBalance + amount
        break
      case 'consumption':
        if (currentBalance < amount) {
          return NextResponse.json({ error: 'Insufficient token balance' }, { status: 400 })
        }
        newBalance = currentBalance - amount
        break
    }

    // Update user balance and create transaction record
    const { error: updateError } = await supabase
      .from('users')
      .update({ token_balance: newBalance })
      .eq('id', user.id)

    if (updateError) {
      console.error('Error updating balance:', updateError)
      return NextResponse.json({ error: 'Failed to update balance' }, { status: 500 })
    }

    const { data: transaction, error: transactionError } = await supabase
      .from('token_transactions')
      .insert({
        user_id: user.id,
        amount: type === 'consumption' ? -amount : amount,
        transaction_type: type,
        description: description || `${type.charAt(0).toUpperCase() + type.slice(1)} of ${amount} tokens`,
        balance_after: newBalance
      })
      .select()
      .single()

    if (transactionError) {
      console.error('Error creating transaction:', transactionError)
      // Try to rollback the balance update
      await supabase
        .from('users')
        .update({ token_balance: currentBalance })
        .eq('id', user.id)
      
      return NextResponse.json({ error: 'Failed to create transaction' }, { status: 500 })
    }

    return NextResponse.json({
      transaction,
      newBalance
    }, { status: 201 })
  } catch (error) {
    console.error('Unexpected error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}