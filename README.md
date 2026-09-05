# ToggleMaster — Tech Challenge Fase 3

Projeto da Pós-graduação FIAP voltado à automação de infraestrutura, CI/CD, DevSecOps e GitOps na AWS. A solução executa cinco microsserviços no Amazon EKS e utiliza Terraform, GitHub Actions, Amazon ECR e Argo CD, respeitando as restrições do AWS Academy.

## Arquitetura

| Camada | Implementação |
|---|---|
| Aplicação | `auth-service`, `flag-service`, `targeting-service`, `evaluation-service` e `analytics-service` |
| Orquestração | Amazon EKS com Services internos `ClusterIP` |
| Imagens | Amazon ECR, com tag do commit e digest SHA-256 |
| Persistência | Três bancos PostgreSQL no Amazon RDS |
| Cache | Amazon ElastiCache for Redis |
| Mensageria | Amazon SQS |
| Dados analíticos | Amazon DynamoDB |
| Infraestrutura como código | Terraform com estado remoto em S3 |
| CI/DevSecOps | GitHub Actions, testes, lint, SAST, SCA e scan de containers |
| CD | Argo CD com sincronização automática da branch `main` |

## Fluxo de entrega

1. Um pull request executa testes, lint, SAST, SCA, build e scan das imagens.
2. Vulnerabilidades críticas bloqueiam o pipeline.
3. Após o merge na `main`, cada serviço publica uma imagem imutável no ECR.
4. O workflow atualiza no Git a imagem do manifesto Kubernetes usando tag e digest.
5. O Argo CD detecta a alteração, sincroniza o EKS e mantém o estado desejado.

Os pipelines não executam `kubectl apply` para implantar os microsserviços. A aplicação do manifesto `Application` é apenas o bootstrap do Argo CD; os deploys seguintes são controlados pelo GitOps.

## Segurança do pipeline

- Go: `go test`, `golangci-lint` e `gosec`.
- Python: compilação, `ruff` e `bandit`.
- Dependências e código-fonte: Trivy em modo filesystem.
- Imagens: build Docker seguido de Trivy.
- Severidade `CRITICAL`: bloqueia a execução quando há correção disponível.
- Credenciais: armazenadas somente em GitHub Secrets e no ambiente local.
- Imagens: publicadas com tag do commit e digest SHA-256.

## Restrições do AWS Academy

- Região: `us-east-1`.
- Conta utilizada na validação: `505980114754`.
- A role preexistente `LabRole` é apenas consultada e reutilizada.
- O Terraform não cria nem modifica IAM Roles ou IAM Policies.
- As credenciais do laboratório são temporárias e nunca devem ser versionadas.
- O Argo CD não possui Load Balancer público; o acesso administrativo deve ser feito por encaminhamento local de porta.

## GitHub Secrets necessários

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN
AWS_REGION
AWS_ACCOUNT_ID
```

As três credenciais temporárias devem pertencer à mesma sessão do AWS Academy e nunca devem ser registradas em arquivos ou mensagens.

## Estrutura principal

```text
TechChallenge3/
├── .github/workflows/
├── analytics-service/
├── auth-service/
├── evaluation-service/
├── flag-service/
├── targeting-service/
├── gitops/
├── infra/
├── k8s/
├── docker-compose.yml
├── README.md
└── RELATORIO_TECNICO.md
```

## Execução local

```bash
docker compose up --build
```

Os microsserviços utilizam as portas `8001` a `8005`.

## Operação no AWS Academy

Após iniciar uma nova sessão, atualize as credenciais locais e os GitHub Secrets. Para conferir a identidade sem revelar as chaves:

```bash
aws sts get-caller-identity
aws eks update-kubeconfig --region us-east-1 --name togglemaster-eks
kubectl get nodes
```

Para conferir o GitOps e a aplicação:

```bash
kubectl -n argocd get application togglemaster
kubectl -n togglemaster get deployments,pods,services
```

O resultado esperado do Argo CD é `Synced` e `Healthy`, com os cinco Deployments disponíveis.

## Estado validado da entrega

Em 5 de setembro de 2026 foram validados:

- cinco pipelines completos aprovados na `main`;
- cinco imagens publicadas no ECR com tag `3af6e83` e digest imutável;
- Argo CD acompanhando a `main` em estado `Synced/Healthy`;
- cinco Deployments disponíveis e cinco pods `Running`, sem reinícios;
- cinco endpoints `/health` respondendo `HTTP 200` com `status: ok`;
- cinco Services `ClusterIP` com endpoints internos ativos;
- três instâncias RDS e o Redis em estado `available`;
- DynamoDB em estado `ACTIVE` e fila SQS acessível;
- reutilização da `LabRole`, sem criação ou alteração de IAM Roles e Policies.

Consulte [RELATORIO_TECNICO.md](RELATORIO_TECNICO.md) para o relatório e o roteiro da apresentação.
