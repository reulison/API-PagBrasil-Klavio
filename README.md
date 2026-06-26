# PagBrasil Webhook Handler

Aplicação em Flask para receber webhooks da PagBrasil, consultar detalhes de assinaturas e enviá-los para o Klaviyo como eventos de automação.

Este projeto é útil para integrações que precisam acompanhar mudanças de status, cobranças e recorrências de assinaturas em tempo real.

## Funcionalidades

- Recebe webhooks em `/webhook/pagbrasil` via `POST`.
- Consulta a API de assinaturas da PagBrasil para obter informações detalhadas da assinatura.
- Envia um evento para o Klaviyo com propriedades relevantes da assinatura.
- Disponibiliza endpoints de saúde e teste para validação rápida.

## Estrutura do projeto

- [app.py](app.py): aplicação principal com rotas, integração com PagBrasil e Klaviyo.
- [requirements.txt](requirements.txt): dependências do projeto.
- [.env.example](.env.example): exemplo de variáveis de ambiente.
- [.gitignore](.gitignore): arquivos que não devem ser enviados para o GitHub.
- [LICENSE](LICENSE): licença do projeto.

## Endpoints

- `POST /webhook/pagbrasil` — recebe o webhook da PagBrasil.
- `GET /health` — retorna status de saúde do serviço.
- `GET /test` — executa uma chamada de teste para a API da PagBrasil.
- `GET /` — informa os endpoints disponíveis.

## Variáveis de ambiente

Crie um arquivo `.env` com as seguintes variáveis:

- `PAGBRASIL_SECRET` — secret da PagBrasil.
- `PAGBRASIL_PBTOKEN` — token da PagBrasil.
- `PAGBRASIL_SUBSCRIPTION_GET_URL` — URL de consulta de assinatura (opcional).
- `KLAVIYO_API_KEY` — chave da API do Klaviyo.
- `PORT` — porta da aplicação (opcional, padrão `8080`).

> Nunca exponha segredos em repositórios públicos. O arquivo [.env.example](.env.example) serve apenas como modelo.

## Exemplo de payload do webhook

```json
{
  "subscription": "99fc3374f17ffaea",
  "amount_brl": 49.9,
  "status": 1,
  "next_billing_date": "2026-07-15"
}
```

O campo mínimo necessário para consultar os detalhes da assinatura é `subscription`.

## Instalação local

1. Crie e ative um ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

No Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Copie o arquivo de exemplo e configure suas variáveis:

```bash
copy .env.example .env
```

Ou no Linux/macOS:

```bash
cp .env.example .env
```

4. Execute a aplicação:

```bash
python app.py
```

Para produção, você pode usar Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:$PORT app:app
```

## Testes rápidos

Health check:

```bash
curl http://localhost:8080/health
```

Endpoint de teste:

```bash
curl http://localhost:8080/test
```

Webhook de teste:

```bash
curl -X POST http://localhost:8080/webhook/pagbrasil \
  -H "Content-Type: application/json" \
  -d '{"subscription":"99fc3374f17ffaea","amount_brl":49.9}'
```

## Como publicar no GitHub

1. Inicialize o repositório local:

```bash
git init
git add .
git commit -m "Initial commit"
```

2. Adicione o remoto do GitHub:

```bash
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
```

3. Envie para o GitHub:

```bash
git branch -M main
git push -u origin main
```

## Deploy

Exemplo rápido para Google Cloud Run:

```bash
gcloud run deploy pagbrasil-webhook \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "PAGBRASIL_SECRET=sua_secret,PAGBRASIL_PBTOKEN=seu_token,KLAVIYO_API_KEY=sua_klaviyo_key"
```

## Dependências

As dependências principais são:

- Flask
- requests
- gunicorn

## Licença

Este projeto está licenciado sob a licença informada no arquivo [LICENSE](LICENSE).
