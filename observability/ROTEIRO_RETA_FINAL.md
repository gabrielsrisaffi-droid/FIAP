# Roteiro da reta final — 16/11/2026

## Situação confirmada

- Cinco serviços instrumentados; Prometheus, Loki e Grafana validados localmente.
- New Relic real: trace com 13 spans, cinco serviços e DynamoDB Local; mapa preservado.
- Grafana → PagerDuty → Discord validado com abertura e resolução do incidente Q1PD89LCQCXT91.
- Recuperação desse ensaio foi manual. Self-healing Kubernetes ainda precisa ser demonstrado.
- Código da Fase 4 está no workspace; publicação e CI remoto ainda pendentes.
- Credenciais atuais autenticaram na conta 639123725828. A documentação e o contexto EKS anteriores apontam para 505980114754. A conta correta deve ser esclarecida antes de provisionar.
- Na conta atual, a consulta não encontrou EKS em us-east-1/us-west-2, nem ECR/RDS/EC2/DynamoDB em us-east-1; nenhum bucket S3 foi listado. LabRole existe. Isso não é uma busca em todas as regiões nem prova de exclusão dos recursos anteriores.

## Enquanto resolvemos o acesso ao laboratório

| Prioridade | Trabalho | Responsável | Critério de conclusão |
|---|---|---|---|
| 1 | Confirmar curso/turma e Learner Lab usado na Fase 3 | Usuário com auxílio do assistente | Conta anterior acessível ou decisão explícita de usar a nova conta |
| 2 | Revisar alterações destinadas à publicação e referências da conta anterior | Assistente | Arquivos necessários identificados; segredos, estados Terraform e temporários fora da publicação |
| 3 | Validar manifests Helm/Kustomize e configuração GitOps final | Assistente | Overlays renderizam; imagens e valores de laboratório definidos; permissões restritas ao necessário |
| 4 | Preparar publicação das cinco imagens instrumentadas | Assistente | Configuração de CI revisada; execução de publicação vinculada às credenciais da conta correta |
| 5 | Organizar evidências e legendas existentes | Assistente | Trace, mapa e JSONs de incidentes vinculados em VALIDACAO.md; ambiente local identificado |
| 6 | Completar identificação da entrega | Usuário | Nomes, RMs, turma e usernames confirmados |
| 7 | Preparar texto de arquitetura e decisões | Assistente | Explicações prontas, com resultados de EKS ainda marcados como pendentes |

Não repetir testes já aprovados sem mudança ou falha nova. O roteiro de gravação e as quatro evidências exigidas estão em EVIDENCIAS.md. Scripts operacionais permanecem fora do corpo do PDF final.

## Quando a conta correta estiver disponível

1. Confirmar identidade, região, EKS, node group, bancos, Redis, SQS, DynamoDB, ECR e backend Terraform por leitura.
2. Se o ambiente anterior existir, avaliar seu estado e reutilizá-lo. Se a nova conta for necessária, preparar configuração e state separados, revisar o plano de criação e estimar novamente o prazo. Não reutilizar automaticamente o state da conta anterior.
3. Atualizar credenciais temporárias locais e do CI sem exibi-las; preservar LabRole sem criar/alterar IAM Roles ou Policies.
4. Publicar as alterações revisadas e as cinco imagens instrumentadas. Confirmar os novos digests nos manifests GitOps.
5. Conferir acesso ao cluster, capacidade dos nós e StorageClass. Criar o Secret de observabilidade na conta/contexto verificados.
6. Implantar chart via ArgoCD com APM, notificações e self-healing habilitados. Confirmar saúde e sincronização das aplicações.
7. Verificar métricas de CPU/memória dos pods, logs, requisições, trace sem cache e mapa no ambiente EKS.
8. Executar uma falha controlada: 503 → alerta → incidente/Discord → PATCH do runbook → novo pod → HTTP 200 → resolução/Discord.
9. Comprovar deduplicação da automação e coletar evidências com horários. Restaurar o overlay normal sem injeção de falha.
10. Fechar relatório e vídeo após a validação real. Conferir links, duração e ausência de credenciais nas capturas.

## Evidências que faltam para concluir

- CI remoto e digests das imagens publicadas.
- Dashboard com CPU/memória reais dos pods no EKS, volume e logs.
- Trace e mapa no ambiente de entrega.
- Incidente e mensagens do ensaio EKS.
- Log do runbook, pod anterior/novo, rollout concluído e avaliação HTTP 200.
- Relatório final, identificação, links e vídeo de até 25 minutos.

## Ordem de prioridade com prazo curto

Resolver a identidade da conta primeiro. Depois garantir aplicação saudável, implantar observabilidade e provar self-healing. Capturar evidências durante cada teste aprovado para evitar repetir o ensaio apenas para gravar telas. Refinamentos visuais e revisão editorial vêm depois da validação técnica.
