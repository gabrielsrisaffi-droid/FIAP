# Executar no VS Code — AWS Academy / Fase 4

Conta esperada: **639123725828**. Região: **us-east-1**.

Abra o terminal integrado do VS Code em **Terminal → Novo Terminal**, usando **PowerShell**. Execute um bloco por vez. O laboratório deve estar verde e as credenciais temporárias devem estar atualizadas no perfil local `default`.

Os comandos usam o workspace isolado já preparado. Não utilizam o state da conta antiga. Não copie chaves, tokens, arquivos de state ou planos binários para o chat.

## Correção do erro de Object Lock (AWS Academy)

O primeiro apply criou o bucket, mas a consulta de Object Lock foi bloqueada pela política do laboratório. **Não execute novamente o plano `bootstrap.tfplan` nem o bloco 1 antigo abaixo.**

Execute no terminal PowerShell:

```powershell
Set-Location 'E:\FIAP\TechChallenge3'
& '.\observability\scripts\repair_academy_bootstrap.ps1'
```

O script verifica conta e proprietário do bucket, salva backup no diretório ignorado pelo Git e retira somente o vínculo `aws_s3_bucket.terraform_state` do estado, preservando o bucket. No workspace isolado, o bucket passa a ser mantido externamente; as três configurações de segurança continuam gerenciadas pelo Terraform. O plano antigo é arquivado como inválido. O script só aplica um novo plano contendo criações ou recursos inalterados para versionamento, criptografia e bloqueio público; qualquer outro resultado interrompe a execução.

Após `BOOTSTRAP CORRIGIDO`, siga para o bloco 2. Se ocorrer erro, pare e envie apenas a mensagem. A correção não altera políticas IAM/SCP nem o workspace da conta antiga.

## 1. Bloco antigo — não executar após o erro de Object Lock

Este bloco cria o bucket `togglemaster-fase4-tfstate-639123725828`, com versionamento, criptografia e bloqueio de acesso público. O plano revisado contém **4 criações, nenhuma alteração e nenhuma exclusão**. Ainda não cria EKS, bancos ou Redis.

Copie o bloco inteiro:

```powershell
Set-Location 'E:\FIAP\TechChallenge3'
$ErrorActionPreference = 'Stop'

function Invoke-Fase4Terraform {
    param([string[]]$Arguments)
    & terraform @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw 'Terraform falhou. Pare aqui e encaminhe somente a mensagem de erro.'
    }
}

$contaFase4 = (& aws sts get-caller-identity --profile default --region us-east-1 --query Account --output text --no-cli-pager | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    throw 'Credenciais AWS nao aceitas. Atualize as credenciais desta sessao antes de continuar.'
}
if ($contaFase4 -ne '639123725828') {
    throw "Conta inesperada: $contaFase4. Nenhum recurso deve ser criado."
}

$env:AWS_PROFILE = 'default'
$env:AWS_REGION = 'us-east-1'
$env:AWS_DEFAULT_REGION = 'us-east-1'

if (-not (Test-Path -LiteralPath 'tmp/phase4-aws-639123725828/bootstrap/bootstrap.tfplan')) {
    throw 'Plano inicial nao encontrado. Avise antes de continuar.'
}

Invoke-Fase4Terraform -Arguments @(
    '-chdir=tmp/phase4-aws-639123725828/bootstrap',
    'apply', '-input=false', '-no-color', 'bootstrap.tfplan'
)
```

Resultado esperado: `Apply complete! Resources: 4 added, 0 changed, 0 destroyed.`

Se houver erro, pare. Se terminar com sucesso, execute o bloco 2 no mesmo terminal. Não repita o bloco 1 depois de uma execução bem-sucedida: o plano salvo já terá sido aplicado.

## 2. Inicializar e planejar a plataforma

Este bloco prepara o backend na nova conta e **gera o plano**, sem criar a plataforma. Downloads de provedores podem demorar alguns minutos.

O planejamento inclui VPC/sub-redes, ECR dos cinco serviços, SQS, DynamoDB, três bancos PostgreSQL privados, Redis privado e EKS com dois nós `t3.medium`. A `LabRole` existente é reutilizada. O endpoint EKS tem acesso privado habilitado e acesso público restrito ao IP identificado durante a preparação. Se você mudou de rede, avise antes da implantação.

```powershell
Set-Location 'E:\FIAP\TechChallenge3'
$ErrorActionPreference = 'Stop'

function Invoke-Fase4Terraform {
    param([string[]]$Arguments)
    & terraform @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Terraform falhou. Pare e encaminhe somente o erro.' }
}
$env:AWS_PROFILE = 'default'
$env:AWS_REGION = 'us-east-1'
$env:AWS_DEFAULT_REGION = 'us-east-1'

Invoke-Fase4Terraform -Arguments @(
    '-chdir=tmp/phase4-aws-639123725828/platform',
    'init', '-input=false', '-no-color', '-backend-config=backend.hcl'
)

Invoke-Fase4Terraform -Arguments @(
    '-chdir=tmp/phase4-aws-639123725828/platform',
    'validate', '-no-color'
)

Invoke-Fase4Terraform -Arguments @(
    '-chdir=tmp/phase4-aws-639123725828/platform',
    'plan', '-input=false', '-no-color', '-out=platform.tfplan'
)
```

## O que enviar ao terminar

Envie apenas:

1. A linha `Apply complete! ...` do bloco 1.
2. A linha `Plan: ... to add, ... to change, ... to destroy.` do bloco 2.
3. Qualquer aviso ou erro exibido, caso exista.

Com o plano conferido, o próximo bloco será a criação da plataforma. Enquanto a AWS provisiona EKS e bancos, podemos preparar a publicação das imagens e os manifests da nova conta.
