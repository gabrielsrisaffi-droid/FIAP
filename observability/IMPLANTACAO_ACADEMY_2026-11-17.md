# Implantacao no AWS Academy — 17/11/2026

Conta: 975049982026
Regiao: us-east-1
Contexto Kubernetes: togglemaster-fase4-975049982026
Tag das imagens: fase4-20261117-185014

## Validacoes realizadas
- Cinco servicos implantados e avaliacao HTTP 200 com result=true.
- Evento correspondente encontrado no DynamoDB por meio do fluxo SQS/analytics.
- Metricas presentes no Prometheus.
- Logs encontrados no Loki nos namespaces togglemaster, observability e kube-system.
- Coleta filelog ampliada para todos os namespaces.
- ArgoCD instalado; sincronizacao das Applications ainda em validacao.

## Recuperacao dos nos
O CloudTrail registrou StopInstances pelo Vocareum as 19h05 de 17/11.
O Auto Scaling substituiu os nos, mas os novos lancamentos falharam com
AccessDenied em kms:Decrypt. A chave estava Enabled e era gerenciada pela AWS.

Como excecao de laboratorio, a copia isolada de eks_nodes.tf passou a usar
encrypted=false no disco raiz dos novos nos. O plano alterou somente o
launch template e o nodegroup. Apply: 0 added, 2 changed, 0 destroyed.
Os dois nos, os workloads e a avaliacao foram verificados apos a recuperacao.

Essa excecao reduz a protecao dos discos dos nos e nao e recomendacao de
producao. Nao houve alteracao da criptografia de RDS, Redis ou bucket de estado.
A fonte generica infra/platform ainda conserva encrypted=true.
Ao reproduzir este laboratorio, avaliar a restricao KMS antes de aplicar.

## GitOps
Durante a validacao, as Applications acompanham codex/techchallenge4-entrega.
A migracao para main deve ocorrer apos merge e revisao das credenciais de CI/CD.
CI aprovado no PR nao comprova publicacao automatizada no ECR.

## Limites
A observabilidade usa armazenamento temporario: historico pode desaparecer
quando os pods ou nos sao substituidos. Evidencias devem ser preservadas fora
do cluster. Nao versionar credenciais, arquivos de estado ou planos Terraform.