# Relatório Técnico — ToggleMaster

## Tech Challenge Fase 3 — DevSecOps e GitOps

## 1. Visão geral

Esta entrega evolui o ToggleMaster para um processo automatizado de provisionamento, validação de segurança e implantação contínua. A infraestrutura AWS é descrita em Terraform, os cinco microsserviços possuem pipelines independentes no GitHub Actions e a entrega no Amazon EKS é controlada pelo Argo CD.

O projeto foi implementado no AWS Academy, em `us-east-1`, reutilizando exclusivamente a `LabRole` disponibilizada pelo laboratório. Nenhuma IAM Role ou IAM Policy é criada ou modificada pelo código.

## 2. Objetivos

- Provisionar a infraestrutura AWS como código com Terraform.
- Automatizar testes, qualidade e segurança dos cinco serviços.
- Bloquear vulnerabilidades críticas conhecidas com correção disponível.
- Publicar imagens Docker imutáveis no Amazon ECR.
- Atualizar manifests Kubernetes de forma rastreável no Git.
- Implantar e reconciliar a aplicação no EKS por GitOps com Argo CD.
- Manter credenciais reais fora do repositório.

## 3. Microsserviços

| Serviço | Responsabilidade | Porta |
|---|---|---:|
| `auth-service` | Criação e validação de API keys | 8001 |
| `flag-service` | Cadastro e consulta de feature flags | 8002 |
| `targeting-service` | Regras de segmentação | 8003 |
| `evaluation-service` | Avaliação, cache e publicação de eventos | 8004 |
| `analytics-service` | Consumo e persistência de eventos analíticos | 8005 |

Os serviços são empacotados individualmente e implantados como Deployments Kubernetes. A comunicação interna utiliza Services `ClusterIP`.

## 4. Infraestrutura como código

O diretório `infra/` possui duas etapas:

- `infra/bootstrap`: cria o bucket usado pelo estado remoto do Terraform.
- `infra/platform`: provisiona rede e serviços da plataforma.

A plataforma contempla VPC, sub-redes públicas e privadas, Amazon EKS e Managed Node Group, cinco repositórios ECR, três bancos PostgreSQL privados no RDS, ElastiCache Redis, SQS, DynamoDB e Security Groups.

As senhas dos bancos são geradas pelo Terraform e marcadas como outputs sensíveis. Credenciais temporárias do AWS Academy não são armazenadas nos arquivos versionados.

## 5. Compatibilidade com AWS Academy

A configuração apenas consulta a role existente:

```hcl
data "aws_iam_role" "academy_lab" {
  name = "LabRole"
}
```

Essa role é reutilizada pelo EKS e pelo node group. O projeto não contém recursos para criar ou modificar IAM Roles e IAM Policies.

As credenciais do laboratório são temporárias. A cada nova sessão, devem ser atualizados o ambiente local e os GitHub Secrets `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_REGION` e `AWS_ACCOUNT_ID`. Seus valores nunca devem aparecer em mensagens, commits, capturas ou documentos.

## 6. CI e DevSecOps

O workflow reutilizável `.github/workflows/_service-ci.yml` é chamado por um workflow de cada microsserviço.

### 6.1 Qualidade e segurança

- Go: testes, `golangci-lint` e SAST com `gosec`.
- Python: compilação, lint com `ruff` e SAST com `bandit`.
- SCA: Trivy analisa dependências do código-fonte.
- Container: build Docker seguido de scan com Trivy.

Achados `CRITICAL` com correção disponível encerram o job com falha.

### 6.2 Eventos do pipeline

- Pull request: executa qualidade, segurança, build e scan; não publica.
- Push na `main`: repete as verificações, publica no ECR e atualiza o manifesto GitOps.

Cada serviço usa uma fila de concorrência própria. Se a `main` avançar durante uma atualização, o workflow sincroniza o histórico e tenta novamente, evitando cancelamentos e perda de commits.

## 7. Imagens imutáveis

Após a aprovação, cada imagem recebe a tag dos sete primeiros caracteres do commit. O pipeline consulta o digest no ECR e grava no manifesto:

```text
repositorio:commit@sha256:digest
```

A tag oferece rastreabilidade e o digest garante a execução exata do artefato verificado. Na validação final, os cinco serviços foram publicados com a tag `3af6e83`.

## 8. GitOps com Argo CD

O arquivo `gitops/argocd/togglemaster-application.yaml` define:

- repositório GitHub do projeto;
- `targetRevision: main`;
- caminho `k8s/base`;
- sincronização automática;
- `prune` e `selfHeal`;
- tentativas com backoff.

Os pipelines não executam `kubectl apply` para implantar os serviços. Eles atualizam o Git, e o Argo CD reconcilia o EKS. O único uso manual de `kubectl apply` é no bootstrap ou na atualização do objeto `Application`.

O Argo CD permanece interno ao cluster e não possui Load Balancer público. O acesso administrativo pode ser feito temporariamente por `kubectl port-forward`.

## 9. Kubernetes

Os manifests desejados ficam em `k8s/base` e são organizados por Kustomize:

- `namespace.yaml`;
- `core-services.yaml` para Auth, Flag e Targeting;
- `event-services.yaml` para Evaluation e Analytics;
- `kustomization.yaml`.

Os Deployments incluem probes, requests e limits, contexto de segurança e referências a ConfigMaps e Secrets. Os Services são internos.

## 10. Fluxo de entrega

```text
Pull request
    ↓
Testes, lint, SAST, SCA, build e scan
    ↓ merge na main
Imagem imutável no ECR
    ↓ commit automático do digest
Manifests em k8s/base
    ↓
Argo CD
    ↓
Amazon EKS
```

O GitHub Actions produz e registra o artefato; o Argo CD controla o deploy.

## 11. Evidências validadas

Em 5 de setembro de 2026 foram observados:

- 10 checks aprovados nos pull requests;
- cinco workflows pós-merge concluídos com sucesso;
- cinco imagens publicadas no ECR;
- cinco commits automáticos atualizando os manifests;
- Argo CD na `main`, em `Synced/Healthy`;
- node do EKS em estado `Ready`;
- cinco pods `Running`, `1/1` e sem reinícios;
- cinco Deployments disponíveis;
- cinco Services `ClusterIP` com endpoints ativos;
- imagens no cluster com tag de commit e digest SHA-256.

## 12. Incidentes e correções

1. Um token temporário expirado impediu a autenticação no AWS Academy. As três credenciais foram renovadas a partir da mesma sessão.
2. Uma fila compartilhada entre os workflows cancelava jobs pendentes. A concorrência foi separada por serviço e foram adicionadas novas tentativas para atualizações simultâneas.
3. Dependências vulneráveis e imagens base dos serviços Go foram atualizadas para eliminar achados críticos bloqueantes.

## 13. Comandos para demonstração

Antes da apresentação, inicie o AWS Academy e atualize as credenciais sem mostrar seus valores.

```bash
aws sts get-caller-identity
kubectl get nodes
kubectl -n argocd get application togglemaster
kubectl -n togglemaster get deployments
kubectl -n togglemaster get pods
kubectl -n togglemaster get services
```

Para mostrar as imagens imutáveis:

```bash
kubectl -n togglemaster get deployments -o custom-columns='DEPLOYMENT:.metadata.name,IMAGE:.spec.template.spec.containers[0].image'
```

Para acessar o Argo CD sem Load Balancer:

```bash
kubectl -n argocd port-forward service/argocd-server 8080:443
```

A interface ficará em `https://localhost:8080`.

## 14. Roteiro da apresentação

1. Apresentar os cinco serviços e os recursos AWS.
2. Mostrar `infra/bootstrap` e `infra/platform`, destacando a `LabRole` existente.
3. Abrir `_service-ci.yml` e explicar os controles DevSecOps.
4. Mostrar os checks aprovados dos pull requests.
5. Mostrar tag e digest nos manifests Kubernetes.
6. Abrir o manifesto do Argo CD e explicar `main`, `prune` e `selfHeal`.
7. Executar os comandos de nodes, deployments, pods e services.
8. Mostrar o Argo CD em `Synced/Healthy`.
9. Reforçar: nenhuma Role/Policy IAM criada e nenhum Load Balancer público para o Argo CD.

## 15. Checklist antes da apresentação

- [ ] AWS Academy iniciado e indicador verde.
- [ ] Credenciais locais renovadas sem compartilhamento.
- [ ] `aws sts get-caller-identity` retorna a conta esperada.
- [ ] `kubectl get nodes` mostra o node `Ready`.
- [ ] Argo CD mostra `Synced/Healthy`.
- [ ] Cinco pods aparecem `Running`.
- [ ] Terminal, navegador e notificações não exibem segredos.
- [ ] PRs e GitHub Actions aprovados estão preparados em abas.

## 16. Conclusão

A Fase 3 acrescentou ao ToggleMaster infraestrutura como código, CI/DevSecOps e CD orientado a GitOps. Os controles verificam código e imagens antes da publicação, os artefatos são rastreáveis e imutáveis, e o Argo CD mantém o EKS alinhado ao estado declarado na `main`.

A solução respeita as limitações do AWS Academy sem criar ou modificar IAM Roles e Policies, mantém credenciais fora do repositório e evita exposição pública do Argo CD. O estado final foi validado com todos os pipelines aprovados e os cinco microsserviços disponíveis no cluster.
