### Pacotes de Tokens (Stripe)
vamos definir ainda os valores para isso.
```javascript
const TOKEN_PACKAGES = [
  { tokens: 10, price: 500 },    // $5.00 - 50¢ per token
  { tokens: 50, price: 2000 },   // $20.00 - 40¢ per token  
  { tokens: 100, price: 3500 },  // $35.00 - 35¢ per token
  { tokens: 500, price: 15000 }, // $150.00 - 30¢ per token
  { tokens: 1000, price: 25000 } // $250.00 - 25¢ per token
]
```

### Compra de Tokens
- **Pagamento**: Apenas Stripe (cartão de crédito/débito)
- **Processamento**: PaymentIntent → Webhook → Crédito automático
- **Falha**: Se webhook falhar, reprocessamento manual necessário
- **Histórico**: Todas as transações são registradas
- **Reembolso**: Apenas via suporte manual (não automático)

## Stripe Webhooks
- **Eventos Monitorados**:
  - `payment_intent.succeeded`
  - `payment_intent.payment_failed`
  - `invoice.payment_succeeded` (para assinaturas futuras)
- **Validação**: Assinatura webhook obrigatória
- **Idempotência**: Processamento de eventos duplicados bloqueado
- **Retry**: Stripe tenta por 3 dias automaticamente#