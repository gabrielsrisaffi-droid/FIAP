# Run from PowerShell. Repairs only the isolated Academy bootstrap, never infra/bootstrap.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repoFase4 = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$bootstrapFase4 = Join-Path $repoFase4 'tmp/phase4-aws-639123725828/bootstrap'
$accountFase4 = '639123725828'
$bucketFase4 = "togglemaster-fase4-tfstate-$accountFase4"
$env:AWS_PROFILE = 'default'
$env:AWS_REGION = 'us-east-1'
$env:AWS_DEFAULT_REGION = 'us-east-1'

function Invoke-RepairAws {
    param([string[]]$Arguments)
    $result = & aws @Arguments --profile default --region us-east-1 --no-cli-pager
    if ($LASTEXITCODE -ne 0) { throw 'AWS falhou. Pare e encaminhe somente o erro, sem credenciais.' }
    return $result
}
function Invoke-RepairTerraform {
    param([string[]]$Arguments)
    $result = & terraform "-chdir=$bootstrapFase4" @Arguments
    if ($LASTEXITCODE -ne 0) { throw 'Terraform falhou. Pare e encaminhe somente o erro.' }
    return $result
}

$identityFase4 = (Invoke-RepairAws -Arguments @('sts', 'get-caller-identity', '--query', 'Account', '--output', 'text') | Out-String).Trim()
if ($identityFase4 -ne $accountFase4) { throw 'Conta diferente da esperada. Nenhuma alteracao realizada.' }
# Verifies existence AND ownership without calling the forbidden Object Lock API.
Invoke-RepairAws -Arguments @('s3api', 'head-bucket', '--bucket', $bucketFase4, '--expected-bucket-owner', $accountFase4) | Out-Null

$stateFileFase4 = Join-Path $bootstrapFase4 'terraform.tfstate'
$stateFase4 = Get-Content -Raw -LiteralPath $stateFileFase4 | ConvertFrom-Json
$allowedFase4 = @('aws_s3_bucket', 'aws_s3_bucket_versioning', 'aws_s3_bucket_server_side_encryption_configuration', 'aws_s3_bucket_public_access_block')
foreach ($resourceFase4 in $stateFase4.resources) {
    if ($resourceFase4.mode -ne 'managed') { continue }
    if ($resourceFase4.type -notin $allowedFase4 -or $resourceFase4.name -ne 'terraform_state') {
        throw 'Recurso inesperado no bootstrap. Revisao necessaria.'
    }
    foreach ($instanceFase4 in $resourceFase4.instances) {
        if ($instanceFase4.attributes.id -ne $bucketFase4) { throw 'Bucket inesperado no estado. Nenhuma alteracao realizada.' }
    }
}

$backupFase4 = Join-Path $bootstrapFase4 ('before-object-lock-repair-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $backupFase4 | Out-Null
foreach ($fileFase4 in @('main.tf', 'security.tf', 'outputs.tf', 'terraform.tfstate')) {
    Copy-Item -LiteralPath (Join-Path $bootstrapFase4 $fileFase4) -Destination $backupFase4
}
$oldPlanFase4 = Join-Path $bootstrapFase4 'bootstrap.tfplan'
if (Test-Path -LiteralPath $oldPlanFase4) {
    Move-Item -LiteralPath $oldPlanFase4 -Destination (Join-Path $backupFase4 'bootstrap.tfplan.invalid')
}
$utf8Fase4 = New-Object System.Text.UTF8Encoding($false)
$mainFase4 = @'
# Academy SCP denies the aws_s3_bucket provider's Object Lock read.
# Existing bucket is retained externally; Terraform manages its security below.
data "aws_caller_identity" "current" {}
locals {
  state_bucket_name = "${var.bucket_prefix}-${data.aws_caller_identity.current.account_id}"
}
'@
[IO.File]::WriteAllText((Join-Path $bootstrapFase4 'main.tf'), $mainFase4, $utf8Fase4)
$securityFase4 = (Get-Content -Raw -LiteralPath (Join-Path $bootstrapFase4 'security.tf')).Replace('aws_s3_bucket.terraform_state.id', 'local.state_bucket_name')
[IO.File]::WriteAllText((Join-Path $bootstrapFase4 'security.tf'), $securityFase4, $utf8Fase4)
$outputsFase4 = @'
output "state_bucket_name" {
  value = local.state_bucket_name
}
output "state_bucket_arn" {
  value = "arn:aws:s3:::${local.state_bucket_name}"
}
'@
[IO.File]::WriteAllText((Join-Path $bootstrapFase4 'outputs.tf'), $outputsFase4, $utf8Fase4)
$addressesFase4 = @(Invoke-RepairTerraform -Arguments @('state', 'list'))
if ($addressesFase4 -contains 'aws_s3_bucket.terraform_state') {
    # Forget the binding only. This does NOT delete the bucket or any object.
    Invoke-RepairTerraform -Arguments @('state', 'rm', 'aws_s3_bucket.terraform_state')
}
Invoke-RepairTerraform -Arguments @('validate', '-no-color')
Invoke-RepairTerraform -Arguments @('plan', '-input=false', '-no-color', '-out=bootstrap-security.tfplan')
$planFase4 = (Invoke-RepairTerraform -Arguments @('show', '-json', 'bootstrap-security.tfplan') | Out-String) | ConvertFrom-Json
$safeAddressesFase4 = @(
    'aws_s3_bucket_versioning.terraform_state',
    'aws_s3_bucket_server_side_encryption_configuration.terraform_state',
    'aws_s3_bucket_public_access_block.terraform_state'
)
foreach ($changeFase4 in $planFase4.resource_changes) {
    if ($changeFase4.mode -ne 'managed') { continue }
    if ($changeFase4.address -notin $safeAddressesFase4 -or
        ($changeFase4.change.actions -join ',') -notin @('create', 'no-op')) {
        throw 'Plano inesperado. Nao aplicado; encaminhe o resumo para revisao.'
    }
}
Invoke-RepairTerraform -Arguments @('apply', '-input=false', '-no-color', 'bootstrap-security.tfplan')
Write-Host 'BOOTSTRAP CORRIGIDO. Bucket preservado; seguranca gerenciada pelo Terraform. Continue no bloco 2 do roteiro.'
