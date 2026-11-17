# Contas para APM e incidentes — sem AWS Academy

Situação em 13/11/2026: Discord disponível; conta New Relic criada pelo usuário na região US, chave configurada localmente e cinco serviços reconhecidos no painel via OpenTelemetry. Atualização de 15/11: serviço PagerDuty, chave Events API v2, token REST de leitura e webhook Discord configurados; fluxo de abertura/resolução testado com sucesso. Atualização de 15/11: trace distribuído dos cinco serviços confirmado; mapa dos cinco serviços confirmado e captura preservada. O laboratório AWS não é necessário para cadastrar essas ferramentas.

## 1. New Relic

1. Abra o [cadastro do New Relic](https://newrelic.com/signup) e crie a conta usando seu próprio e-mail. Conclua a confirmação solicitada pela plataforma.
2. Anote a região da conta. O Collector usa inicialmente o endpoint dos Estados Unidos; uma conta europeia precisa de `https://otlp.eu01.nr-data.net`.
3. Na tela de [API keys](https://docs.newrelic.com/docs/apis/intro-apis/new-relic-api-keys/), localize a **ingest license key** da conta. Essa é a chave destinada ao recebimento da telemetria.
4. Preencha `NEW_RELIC_LICENSE_KEY` no arquivo local `observability/.env`.

O projeto já está instrumentado com OpenTelemetry e envia HTTP/protobuf. O endpoint e o cabeçalho `api-key` seguem a [configuração OTLP oficial](https://docs.newrelic.com/docs/opentelemetry/best-practices/opentelemetry-otlp/). Não é preciso instalar outro agente APM nos cinco serviços para este desenho.

## 2. PagerDuty

1. Acesse o [PagerDuty](https://www.pagerduty.com/) e crie a conta. Confira a modalidade oferecida no cadastro e eventual prazo de avaliação antes de planejar a gravação.
2. Crie um serviço chamado `ToggleMaster-FIAP`, com sua política de escalonamento e você como responsável pelo ensaio.
3. Adicione uma integração **Events API V2**. Copie a chave dessa integração para `PAGERDUTY_ROUTING_KEY`.
4. Identifique o ID do serviço e preencha `PAGERDUTY_SERVICE_ID`.
5. Em **Integrations → Developer Tools → API Access Keys**, crie uma chave REST com a opção **Read-only API Key**. Coloque-a em `PAGERDUTY_API_TOKEN`.

As chaves são diferentes: Grafana usa a chave Events API para abrir/resolver incidentes; o bridge usa o token REST somente para consultar o serviço e encaminhar mudanças ao Discord. Referências: [serviços e integrações](https://docs.pagerduty.com/incident-management/services), [Events API v2](https://docs.pagerduty.com/developer/events-api-v2-overview) e [API Access Keys](https://docs.pagerduty.com/account-admin/api-access-keys).

## 3. Discord

No servidor do trabalho, escolha um canal de texto, por exemplo `incidentes-fiap`. Em configurações do servidor, abra **Integrações → Webhooks**, crie o webhook e selecione esse canal. Preencha `DISCORD_WEBHOOK_URL` com a URL copiada. Veja o [guia oficial do Discord](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks).

Testes autorizados concluídos em 15/11: mensagem direta e notificações de abertura/resolução de incidente entregues ao Discord. Evidências em VALIDACAO.md.

## 4. Conferência local

As credenciais locais do Grafana e do runbook já foram geradas em `observability/.env`, que está ignorado pelo Git. Preserve os valores de `GF_SECURITY_ADMIN_PASSWORD` e `RUNBOOK_TOKEN`; complete somente os campos das contas externas. Não envie chaves pelo chat.

Na raiz do repositório:

```powershell
.venv-fase4/Scripts/python.exe observability/scripts/check_readiness.py --integrations
```

O comando informa os campos pendentes sem imprimir os valores. Ele verifica preenchimento e formato; a autenticidade das chaves só será confirmada durante a integração real.

Depois do cadastro, informe apenas que as contas estão prontas e qual é a região do New Relic. A partir daí, podemos validar o APM com a aplicação local antes de ativar o AWS Academy.
