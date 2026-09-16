# Desafios Encontrados e Decisões Tomadas

## Credenciais temporárias do AWS Academy

As credenciais do laboratório expiram ao final de cada sessão, interrompendo o acesso local à AWS e a autenticação dos workflows.

**Decisão:** carregar as credenciais somente nas variáveis de ambiente do terminal e nos GitHub Secrets. Nenhuma credencial foi registrada no repositório. A solução reutiliza exclusivamente a `LabRole` existente e não cria nem modifica IAM Roles ou IAM Policies.

## Restrições de acesso ao EKS

O acesso à API do EKS apresentou timeout quando o endereço IP público autorizado mudou entre sessões do laboratório.

**Decisão:** manter o endpoint protegido e atualizar no Terraform somente o CIDR `/32` autorizado, em vez de liberar acesso irrestrito.

## Concorrência nas atualizações GitOps

Os cinco pipelines podem concluir próximos uns dos outros e tentar atualizar a branch `main` simultaneamente. Uma fila de concorrência compartilhada chegou a cancelar execuções pendentes.

**Decisão:** separar a concorrência por microsserviço e adicionar novas tentativas de `git pull`, rebase e push. Assim, cada workflow atualiza seu próprio manifesto sem cancelar os demais.

## Bloqueios de segurança no pipeline

O SAST identificou uma chamada propositalmente insegura com `shell=True`, classificada pelo Bandit como B602 de severidade alta. O scan de containers também encontrou vulnerabilidades críticas corrigíveis em pacotes das imagens-base.

**Decisão:** preservar os bloqueios do pipeline, remover a implementação insegura e atualizar os pacotes das imagens antes do merge. O código inseguro não foi incorporado à `main`.

## Inicialização segura dos bancos

A preparação dos bancos exigiu coordenar ConfigMaps, Jobs e Secrets sem registrar senhas nos manifestos. Também foi necessário normalizar quebras de linha do Windows para comandos executados nos containers Linux.

**Decisão:** utilizar Jobs idempotentes de inicialização, gerar senhas fora do Git e manter no Kubernetes apenas Secrets criados em tempo de execução. Os usuários das aplicações receberam permissões específicas para seus próprios bancos.

## Implantação controlada por GitOps

Executar `kubectl apply` dentro dos pipelines reduziria a rastreabilidade e contrariaria o modelo GitOps solicitado.

**Decisão:** os workflows publicam imagens imutáveis no ECR e atualizam no Git a tag e o digest SHA-256. O Argo CD acompanha a branch `main`, aplicando sincronização automática, `prune` e `selfHeal`.

## Exposição do Argo CD

Um Load Balancer público para a interface administrativa aumentaria custo e superfície de exposição.

**Decisão:** manter o Argo CD somente dentro do cluster e, quando necessário, acessá-lo por `kubectl port-forward`.

