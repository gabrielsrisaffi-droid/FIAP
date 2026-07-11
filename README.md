# ToggleMaster - Tech Challenge Fase 2

Projeto desenvolvido para o Tech Challenge da Pós-graduação FIAP, com foco em modernização de uma aplicação monolítica para uma arquitetura baseada em microsserviços, containers, Kubernetes e serviços gerenciados AWS.

## Visão Geral

O ToggleMaster é uma plataforma de gerenciamento e avaliação de feature flags. A solução foi dividida em cinco microsserviços independentes:

- `auth-service`: responsável pela geração e validação de API Keys.
- `flag-service`: responsável pelo cadastro e consulta de feature flags.
- `targeting-service`: responsável pelas regras de segmentação das flags.
- `evaluation-service`: responsável pela avaliação das flags para usuários específicos.
- `analytics-service`: responsável pelo consumo de eventos e persistência analítica.

## Arquitetura Local

Para execução local, o projeto utiliza Docker Compose com os seguintes componentes:

- 5 microsserviços containerizados.
- 2 bancos PostgreSQL locais.
- Redis.
- LocalStack para simulação do SQS.
- DynamoDB Local.
- Serviço auxiliar `local-init` para criação automática da fila SQS e da tabela DynamoDB.

## Arquitetura AWS

Na AWS Academy, a aplicação foi implantada utilizando:

- Amazon EKS para orquestração Kubernetes.
- Amazon ECR para armazenamento das imagens Docker.
- Amazon RDS PostgreSQL para persistência relacional.
- Amazon ElastiCache Redis para cache.
- Amazon SQS para mensageria.
- Amazon DynamoDB para armazenamento analítico.
- Nginx Ingress Controller para exposição HTTP.
- Horizontal Pod Autoscaler para escalabilidade automática.

## Docker Compose

O Docker Compose foi utilizado para orquestração local dos microsserviços e dependências. Já os manifests Kubernetes foram utilizados para implantação no EKS, separando responsabilidades em Deployments, Services, ConfigMaps, Secrets, HPAs e Ingress, com probes e limites de recursos para maior resiliência e escalabilidade.

## Como executar localmente

Na raiz do projeto, execute:

```bash
docker compose up --build
```

Esse comando irá:

- Construir as imagens dos cinco microsserviços.
- Subir os bancos PostgreSQL locais.
- Executar automaticamente os scripts SQL iniciais.
- Subir o Redis.
- Subir o LocalStack para simulação do SQS.
- Subir o DynamoDB Local.
- Criar automaticamente a fila SQS `togglemaster-events`.
- Criar automaticamente a tabela DynamoDB `ToggleMasterAnalytics`.

## Serviços locais

| Serviço | Porta |
|---|---:|
| auth-service | 8001 |
| flag-service | 8002 |
| targeting-service | 8003 |
| evaluation-service | 8004 |
| analytics-service | 8005 |
| PostgreSQL Auth | 5433 |
| PostgreSQL Flags/Targeting | 5434 |
| Redis | 6379 |
| LocalStack | 4566 |
| DynamoDB Local | 8000 |

## Health checks locais

Após subir o ambiente, os serviços podem ser validados pelos endpoints de health check:

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
```

## Kubernetes

Os manifests Kubernetes limpos para entrega estão na pasta:

```text
k8s-clean/
```

Essa pasta contém:

- Namespace.
- ConfigMap.
- Secrets de exemplo.
- Deployments.
- Services.
- Horizontal Pod Autoscalers.
- Ingress.

Os manifests foram validados com:

```bash
kubectl apply --dry-run=client -f k8s-clean
```

## Segurança

As credenciais reais não foram versionadas nos manifests finais.

O arquivo abaixo contém apenas exemplos e placeholders:

```text
k8s-clean/02-secrets.example.yaml
```

No ambiente real, os valores sensíveis devem ser criados como Secrets do Kubernetes, incluindo:

- URLs de conexão dos bancos RDS.
- Master Key do serviço de autenticação.
- API Key usada entre serviços.
- Credenciais temporárias do AWS Academy.

## Evidências de funcionamento

Durante a execução do projeto, foram validados:

- Build dos cinco microsserviços via Docker Compose.
- Execução local completa com Docker Compose.
- Criação automática das tabelas PostgreSQL locais.
- Criação automática da fila SQS local no LocalStack.
- Criação automática da tabela DynamoDB Local.
- Implantação da aplicação no Amazon EKS.
- Push das imagens Docker para o Amazon ECR.
- Integração com Amazon RDS PostgreSQL.
- Integração com Amazon ElastiCache Redis.
- Integração com Amazon SQS.
- Integração com Amazon DynamoDB.
- Exposição externa via Nginx Ingress Controller.
- Configuração de HPA para `evaluation-service` e `analytics-service`.

## Estrutura principal do projeto

```text
TechChallenge2/
├── auth-service/
├── flag-service/
├── targeting-service/
├── evaluation-service/
├── analytics-service/
├── local-init/
├── k8s-clean/
├── k8s-final/
├── docker-compose.yml
└── README.md
```

## Observação sobre ambiente AWS Academy

A implantação em nuvem foi realizada considerando as limitações do ambiente AWS Academy, utilizando a role `LabRole` e os recursos disponíveis no laboratório.

As credenciais temporárias do AWS Academy precisam ser atualizadas sempre que o laboratório for reiniciado.