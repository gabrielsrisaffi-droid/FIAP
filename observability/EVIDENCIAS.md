# Roteiro de validação e entrega — Fase 4

Este arquivo é material de preparação. Nenhuma captura ou resultado de nuvem foi fabricado. A entrega final será fechada somente depois do ensaio real.

Em 12/11/2026, o ensaio Docker local comprovou avaliação, persistência, métricas, logs e ciclo do alerta. Os [registros locais](VALIDACAO.md) identificam explicitamente a remoção manual da falha. Eles ajudam na preparação e não substituem o mapa APM nem a recuperação automática no EKS.

## Antes da gravação

- Confirmar os cinco serviços funcionando com as imagens instrumentadas.
- Verificar pipelines DevSecOps, Terraform e ArgoCD das fases anteriores.
- Abrir Grafana, New Relic, PagerDuty e Discord nas telas necessárias.
- Preparar uma flag habilitada com regra percentual de 100%, usando dados sintéticos.
- Confirmar tráfego saudável e anotar o horário inicial.
- Confirmar que o arquivo de falha não existe, que o alvo tem uma réplica no laboratório e que a opção de injeção está habilitada somente para o ensaio.
- Conferir que as chaves não aparecem em terminais, logs, URLs compartilhadas ou capturas.

## Ensaio completo do incidente

1. Gerar duas avaliações por segundo durante o ensaio. Anotar um trace ID de cache miss.
2. Mostrar o dashboard com volume de requisições, CPU, memória e logs.
3. Criar `/tmp/togglemaster-fault` no pod evaluation. O processo permanece em execução e `/health` continua retornando 200.
4. Comprovar os 503, a regra pendente e depois firing. O primeiro contador deve ter duas amostras para produzir uma taxa; aguardar a janela de observação.
5. Mostrar o incidente criado pelo Grafana no PagerDuty e a notificação correspondente no Discord. O bridge consulta a cada 30 segundos; medir esse atraso na execução real.
6. Capturar o log `restart_requested` do runbook, o horário e o pod anterior/novo. Conferir `kubectl rollout status deployment/evaluation-service -n togglemaster --timeout=120s`.
7. Mostrar nova avaliação HTTP 200. O arquivo temporário desaparece na substituição do pod.
8. Manter tráfego para que a janela de erros esvazie. Registrar a resolução do alerta, do incidente e sua notificação no Discord.
9. Confirmar que notificações repetidas do mesmo evento não provocaram outro reinício.
10. Remover a configuração de injeção pelo GitOps e voltar ao overlay normal.

Se a automação falhar, coletar o erro real e corrigir antes de gravar a demonstração final. O log de PATCH aceito não comprova sozinho a recuperação. Usar o novo pod saudável e a resposta da API como evidência de resultado.

## Roteiro do vídeo: meta de 24 minutos

| Tempo | Conteúdo |
|---|---|
| 00:00–03:00 | Problema, arquitetura, cinco serviços e continuidade das fases 1–3 |
| 03:00–06:00 | Repositório, CI/CD, imagens, Helm e ArgoCD |
| 06:00–10:00 | Collector, dashboard de CPU/memória/volume e logs ao vivo |
| 10:00–14:00 | APM: trace de uma avaliação, cache miss, HTTP, fila e mapa de serviços |
| 14:00–22:30 | Falha, alerta, PagerDuty, Discord, runbook e recuperação real |
| 22:30–24:00 | Justificativas, evidências e links de entrega |

O limite do enunciado é 25 minutos. Ajustar o roteiro após medir o tempo de detecção e resolução, mantendo a sequência verificável.

## Estrutura do relatório final

1. Identificação: nomes, RMs e usernames dos integrantes, turma e demais dados pedidos pela FIAP.
2. Links verificáveis do repositório e do vídeo.
3. Arquitetura e responsabilidade das ferramentas, com explicação breve do fluxo.
4. Quatro capturas reais exigidas, com horário e legenda: dashboard Grafana; trace distribuído no APM; notificação do incidente no Discord; log ou execução do self-healing.
5. Justificativas: métricas no Prometheus, logs no Loki, visualização/alertas no Grafana, coleta central OTLP, New Relic para APM e PagerDuty/Discord para incidentes.
6. Resultado da automação: falha aplicada, gatilho, ação permitida e comprovação da recuperação.

Usar apenas resultados observados. O relatório final não deve afirmar que a etapa AWS ou o mapa APM foram validados antes da execução. Manter scripts operacionais e checklists fora do corpo do PDF; usar o repositório como referência técnica.

## Registro de execução a preencher

| Campo | Valor observado |
|---|---|
| Commit/digests das cinco imagens | Pendente |
| Data e intervalo do ensaio | Pendente |
| Trace ID completo da avaliação | Pendente |
| Cinco serviços visíveis no mapa APM | Pendente |
| Horário do primeiro 503 | Pendente |
| Horário em que o alerta disparou | Pendente |
| ID e horário do incidente PagerDuty | Pendente |
| Notificação no Discord | Pendente |
| Horário do PATCH e troca de pod | Pendente |
| Primeiro HTTP 200 após recuperação | Pendente |
| Alerta/incidente resolvidos | Pendente |
| Links e duração final do vídeo | Pendente |

Os testes locais são evidência técnica de preparação, não substitutos das capturas do sistema funcionando no ambiente de entrega.
