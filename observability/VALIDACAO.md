# Registro de validação local — atualizado em 12/11/2026

Ambiente: Windows; Go 1.26.4; Python 3.12.14 em `.venv-fase4`; Helm 3.19.0; OpenTelemetry Collector Contrib 0.165.0; Prometheus/promtool 3.16.0. Binários Helm, Collector e Prometheus baixados das distribuições oficiais e conferidos por SHA-256. As imagens Python usam Python 3.11. Em 12/11, Docker Engine 29.4.0 iniciou e permitiu o ensaio integrado.

Os testes de componentes começaram em 08/11; a retentativa HTTP, os cenários PromQL e o ensaio em containers foram concluídos até 12/11.

| Verificação | Resultado observado |
|---|---|
| Auth: `go test ./...` | Aprovado; 1 teste |
| Evaluation: `go test ./...` | Aprovado; 4 testes |
| Auth e evaluation: `go vet ./...` | Aprovado |
| Telemetria Python em flag, targeting e analytics | Aprovado; 1 teste por serviço, processos separados |
| Automação de incidentes | 11 casos aprovados, incluindo recuperação após falha temporária e repetição do webhook |
| Pipeline com Collector real | 1 teste aprovado |
| Casos Go/Python distintos | **20 aprovados** |
| Cenários de alerta no promtool | **9 aprovados**; limiar, duração, recuperação, reset de contador e isolamento de serviço |
| Consultas PromQL do dashboard | 7 consultas analisadas pelo promtool |
| Ruff nos serviços Python, automação, scripts e testes | Aprovado |
| Bandit no código de automação | Aprovado; supressões específicas e justificadas para HTTPS e bind do serviço Kubernetes |
| Helm lint e renderização | 14 recursos no padrão; 25 com APM, notificações, recuperação e persistência habilitados |
| YAML interno/JSON/RBAC/overlays | Validados; cinco Deployments instrumentados |
| Docker Compose config | Aprovado para observabilidade e composição com os serviços |
| Collector validate | Aprovado no pipeline central e na combinação com configuração New Relic |
| Build e inicialização dos cinco serviços | Aprovados no Docker local |
| Avaliação → SQS → analytics → DynamoDB | Avaliação retornou true; 430 eventos sintéticos no DynamoDB local na captura pós-recuperação |
| Grafana + Prometheus + Loki | Banco Grafana saudável; oito painéis provisionados; ambos os datasources com status OK |
| Métricas/logs reais | Contadores HTTP dos quatro serviços com endpoints de negócio; logs dos cinco serviços presentes no Loki |
| Falha e alerta reais | Injeção → HTTP 503 → pending → firing → remoção manual → HTTP 200 → inactive |

O teste com Collector detectou e permitiu corrigir uma colisão entre `service.name` do recurso e `service_name` no datapoint. O rótulo de serviço agora vem do recurso. O teste também confirmou os nomes Prometheus usados nas consultas e a remoção de query strings dos spans.

Os testes Python exibem avisos de depreciação de dependências existentes Flask/Werkzeug no Python 3.12 e do handler de logs do SDK. Não houve falha; as imagens Python 3.11 foram compiladas e executadas no ensaio de 12/11. O scan remoto de imagens ainda está pendente.

## Ensaio integrado de 12/11

O primeiro início real do Grafana identificou que `interval: 15s` não era múltiplo do intervalo padrão de seu scheduler. A regra foi corrigida para 30 segundos e os testes PromQL passaram a usar o mesmo intervalo do arquivo provisionado.

Horários convertidos para America/Sao_Paulo (UTC−03:00):

| Evento observado | Horário |
|---|---|
| Falha injetada e primeira resposta 503 | 19:22:24 |
| Alerta pendente | 19:23:14 |
| Alerta disparado | 19:24:14 |
| Arquivo de falha removido manualmente; API respondeu 200 | 19:24:14 |
| Alerta resolvido | 19:26:45 |

Tempo observado até firing: aproximadamente 110 segundos. Após restaurar o serviço, aproximadamente 150 segundos até resolução. Esses valores incluem a janela móvel de dois minutos, exportação/scrape e avaliação do Grafana; não são garantias de latência.

O gerador encerrou normalmente após oito minutos: 959 requisições, sendo 739 respostas 200 e 220 respostas 503 durante a falha intencional. Ao final, foi confirmada a ausência do arquivo de falha; os cinco serviços e a stack local permaneceram em execução.

Evidências locais, sem credenciais: [baseline](evidence/local-2026-11-12/baseline.json), [sequência do alerta](evidence/local-2026-11-12/alert-cycle.json) e [estado recuperado](evidence/local-2026-11-12/recovered.json). Os JSONs preservam os horários originais em UTC.

A recuperação deste ensaio foi **manual**, removendo o arquivo de falha no container. O teste comprova detecção e resolução no Grafana, mas não é evidência de self-healing em Kubernetes.

## Novo ensaio New Relic — 13/11/2026

O Docker Desktop estava fechado e foi iniciado novamente, sem AWS. A stack de observabilidade foi retomada com o override New Relic e o bootstrap local respondeu com avaliação verdadeira. O gerador passou a deixar o serviço criar o span raiz por padrão; anteriormente injetava um `traceparent` cujo span pai não era exportado. Essa correção evita traces incompletos, mas ainda não comprova a causa da tela vazia no New Relic.

Foram executadas 60 requisições em 60 segundos, todas HTTP 200. Após o ensaio, `otelcol_exporter_sent_spans` do exportador `otlp_http/newrelic` registrou 335 spans enviados ao endpoint US nesta execução do Collector (inclui bootstrap; não equivale a 335 traces). O Ruff do gerador passou.

Capturas posteriores enviadas pelo usuário confirmaram 61 traces de `GET /evaluate`, zero erros e p95 de 14,06 ms. O detalhe do trace `c68ff82eac40fcd00f30e3dc455e37d6` mostrou cinco spans, duração total de 8,7 ms e o caminho evaluation-service → envio à fila → analytics-service → DynamoDB Local. O mapa incluiu dois serviços e a dependência `aws.dynamodb`; esse rótulo não indica uso da AWS real neste ensaio. Naquela sessão, restava inspecionar um trace sem cache e o mapa envolvendo os cinco serviços. O cache de dados de flag dura 30 segundos e dispensa as consultas a flag/targeting enquanto válido.

## Retomada local — 15/11/2026

Docker Desktop e os dois projetos Compose retomados com override New Relic. Bootstrap aprovado; carga de 75 segundos a uma requisição por segundo terminou com 75 respostas HTTP 200. Os logs confirmaram cache HIT e MISS. O contador do exportador New Relic registrou 410 spans enviados nesta execução do Collector após a carga. Isso confirma envio pelo exportador, não a inspeção do novo trace no painel.

O verificador local passou: saúde HTTP 200 dos cinco serviços, Grafana saudável, oito painéis provisionados, Prometheus/Loki saudáveis, métricas HTTP dos quatro serviços síncronos, logs dos cinco serviços, alerta inativo/saudável e eventos sintéticos persistidos no DynamoDB Local. AWS Academy não iniciado. As capturas posteriores confirmaram as cinco aplicações no mesmo trace, conforme descrito abaixo.

## Trace dos cinco serviços confirmado — 15/11/2026

As duas capturas fornecidas pelo usuário mostram o mesmo trace GET /evaluate com **13 spans, 18,58 ms, zero erros e seis entidades**. Os cinco serviços estão identificados na árvore: evaluation-service, targeting-service, flag-service, auth-service e analytics-service. O sexto componente corresponde à dependência DynamoDB, cuja operação PutItem aparece ao final. O ambiente continua sendo Compose com DynamoDB Local e LocalStack.

O caminho observado inclui evaluate.flag, chamadas HTTP para targeting e flag, chamadas de ambos ao GET /validate de auth, envio togglemaster-events, processamento no analytics e DynamoDB PutItem. Isso confirma a correlação entre os cinco serviços e a fila em um mesmo trace. O painel também marca um span como anômalo; a causa desse indicador não foi investigada e ele não altera o contador observado de zero erros. Uma captura adicional do Entity map confirmou visualmente evaluation → targeting/flag → auth e evaluation → analytics → DynamoDB. As seis entidades correspondem aos cinco serviços e à dependência DynamoDB Local. Evidência: [mapa do trace](evidence/local-2026-11-15/newrelic-entity-map.png). A validação local do trace e de seu mapa está concluída; a demonstração no EKS continua pendente.

Evidências preservadas: [chamadas HTTP](evidence/local-2026-11-15/newrelic-trace-http.png) e [fila e DynamoDB](evidence/local-2026-11-15/newrelic-trace-queue.png).

## Teste direto do Discord — 15/11/2026

Com autorização explícita do usuário, foi publicada uma única mensagem sintética pelo webhook configurado localmente: "Teste FIAP — integração com Discord configurada. Nenhum incidente real."

O POST com wait=true retornou HTTP 200, identificador de mensagem presente e conteúdo igual ao autorizado. Menções foram desativadas no payload. Esse teste confirma a publicação direta pelo webhook; não valida ainda o fluxo Grafana → PagerDuty → bridge → Discord. Nenhum incidente foi criado no PagerDuty neste teste. Credenciais permanecem apenas no .env ignorado pelo Git.

## Fluxo externo completo confirmado — 15/11/2026

Ensaio autorizado pelo usuário: Grafana → PagerDuty → bridge → Discord, com falha controlada e recuperação manual no Compose. O token REST de leitura identificou corretamente o serviço ToggleMaster-FIAP (HTTP 200), e não havia incidentes ativos antes do ensaio. A nova configuração Compose passou na validação; Ruff aprovado e 11 testes de automação aprovados.

Horários abaixo em Brasília (UTC−3):

| Evento | Horário |
|---|---|
| Falha injetada; avaliação HTTP 503 | 13:13:57 |
| Grafana pending | 13:14:47 |
| Incidente PagerDuty criado | 13:15:46 |
| Grafana firing observado; falha removida; HTTP 200 | 13:15:47 |
| Discord confirmou notificação triggered | 13:15:55 |
| Grafana inactive observado | 13:18:18 |
| PagerDuty resolved observado | 13:18:27 |
| Discord confirmou notificação resolved | 13:18:31 |

Incidente: Q1PD89LCQCXT91, título [FIAP TESTE LOCAL] EvaluationHighErrorRate - falha controlada. A consulta posterior confirmou que permanece resolvido. Os tempos de observação incluem intervalos de polling; não são os tempos exatos de todas as transições. O processo de carga foi iniciado para 360 segundos; seu resumo final não foi recuperado após interrupção da sessão, portanto não se declara um total exato de requisições.

Evidências: [ciclo Grafana](evidence/local-2026-11-15/external-alert-cycle.json), [ciclo PagerDuty](evidence/local-2026-11-15/pagerduty-cycle.json) e [entregas Discord](evidence/local-2026-11-15/discord-incident-delivery.json). O bridge foi parado após o teste e o Grafana voltou à configuração local sem notificações externas. O envio APM foi preservado. Ainda falta o ensaio real de self-healing no EKS. Na retomada do Docker, a primeira verificação encontrou ausência de métricas recentes e dados temporários do DynamoDB Local; após bootstrap e carga saudável, a verificação completa passou novamente. Registro: [saúde após retomada](evidence/local-2026-11-15/recovered-after-external-test.json).

## Limites desta validação

- O problema anterior do Docker foi superado com uma nova inicialização. O Compose completo foi executado; a inspeção visual final do dashboard permanece pendente.
- Grafana, Prometheus e Loki reais foram verificados localmente. A conta New Relic US foi criada pelo usuário e o override APM está habilitado. Capturas do usuário em 13/11 confirmam os cinco serviços reconhecidos via OpenTelemetry e um trace com avaliação, fila, analytics e DynamoDB Local. Em 15/11, as capturas confirmaram também o caminho HTTP envolvendo flag, targeting e auth no mesmo trace de avaliação e analytics. O mapa desse trace também foi confirmado visualmente e sua captura foi preservada.
- O Collector do nó precisa do certificado/token de ServiceAccount e kubelet do cluster; essa inicialização autenticada não foi concluída no Windows.
- Discord direto e fluxo Grafana → PagerDuty → bridge → Discord validados, incluindo abertura e resolução do incidente de teste. Recuperação manual no Compose; self-healing Kubernetes pendente.
- O webhook foi testado por HTTP local; o PATCH real e a conclusão do rollout dependem do cluster.
- Bootstrap, carga e falha controlada foram executados contra a stack local completa, com LocalStack/SQS e DynamoDB Local.
- CI remoto, scan de imagens, demonstração APM no EKS, demais capturas finais e vídeo ainda estão pendentes. Trace e mapa dos cinco serviços foram validados no Compose com New Relic real. Não houve commit, push nem alteração de recursos AWS.

As alterações são uma preparação verificável para a Fase 4, não a conclusão da entrega acadêmica.
