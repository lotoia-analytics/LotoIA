# LotoIA Landing (lotoia.chat)

Landing page Next.js 14 para assinatura via WhatsApp + PIX.

## Stack

- Next.js 14 (App Router)
- Tailwind CSS
- TypeScript

## Desenvolvimento local

```bash
cd lotoia-landing
npm install
npm run dev
```

Preview: http://localhost:3000

## Deploy Railway

1. Criar **novo serviço** no projeto Railway
2. Root Directory: `lotoia-landing`
3. Build: `npm run build`
4. Start: `npm run start`
5. Domínio customizado: `lotoia.chat` (Etapa 4)

## API

- `POST /api/checkout` — mock PIX (Etapa 2 integra Asaas real)

```json
{
  "nome": "Kleyson",
  "whatsapp": "66992358330",
  "plano": "pro"
}
```
