#requires -Version 5.1
<#
Inicializacao dos usuarios PostgreSQL de aplicacao do ToggleMaster.
Salvar em k8s/bootstrap/initialize-app-databases.ps1.
Nao modifica fontes, Terraform ou senhas administrativas.
Gera novas senhas apenas em memoria e envia-as para Kubernetes Secrets.
Execucao inicial: se encontrar alvos existentes, para sem sobrescreve-los.
Nao utilizar Start-Transcript, Set-PSDebug ou dumps dos objetos deste script.
#>
[CmdletBinding()]
param([switch]$ValidateOnly)

$ErrorActionPreference = 'Stop'
$EksContext = 'arn:aws:eks:us-east-1:505980114754:cluster/togglemaster-eks'
$Namespace = 'togglemaster'

function Invoke-KubeRead {
    param([string[]]$KubeArguments)
    $Raw = & kubectl --context $EksContext '--request-timeout=30s' @KubeArguments
    if ($LASTEXITCODE -ne 0) {
        throw 'Falha na consulta ao Kubernetes. Operacao interrompida.'
    }
    $Text = $Raw -join "`n"
    if (-not [string]::IsNullOrWhiteSpace($Text)) {
        return ($Text | ConvertFrom-Json)
    }
}

function Submit-KubeCreate {
    param($Resource, [switch]$DryRun)
    $KubeArguments = @('--context', $EksContext, '--request-timeout=30s', 'create', '-f', '-')
    if ($DryRun) { $KubeArguments += '--dry-run=server' }
    $Resource | ConvertTo-Json -Depth 30 -Compress | & kubectl @KubeArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao criar/validar $($Resource.kind)/$($Resource.metadata.name). Nao repita sem verificar o estado."
    }
}

function Read-SecretField {
    param($Secret, [string]$Field)
    $Property = $Secret.data.PSObject.Properties[$Field]
    if ($null -eq $Property -or [string]::IsNullOrWhiteSpace([string]$Property.Value)) {
        throw "Secret $($Secret.metadata.name) sem o campo obrigatorio $Field."
    }
    return [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Property.Value))
}

function Get-ObjectMetadata {
    param([string]$Name)
    return @{
        name = $Name
        namespace = $Namespace
        labels = @{
            'app.kubernetes.io/part-of' = 'togglemaster'
            'app.kubernetes.io/component' = 'db-app-bootstrap'
            'app.kubernetes.io/managed-by' = 'togglemaster-bootstrap'
        }
    }
}

$Databases = @(
    @{ Service = 'auth'; Database = 'auth_db'; Role = 'toggle_auth_app'; Table = 'api_keys'; Grants = 'SELECT, INSERT'; CanModify = 'false' },
    @{ Service = 'flag'; Database = 'flags_db'; Role = 'toggle_flag_app'; Table = 'flags'; Grants = 'SELECT, INSERT, UPDATE, DELETE'; CanModify = 'true' },
    @{ Service = 'targeting'; Database = 'targeting_db'; Role = 'toggle_targeting_app'; Table = 'targeting_rules'; Grants = 'SELECT, INSERT, UPDATE, DELETE'; CanModify = 'true' }
)

# Nomes interpolados abaixo pertencem exclusivamente ao mapa fixo acima.
# Senha interpolada pelo psql como literal SQL escapado, sem argumentos de CLI.
$CreateSqlTemplate = @'
\set ECHO none
\set ON_ERROR_STOP on
\getenv app_password APP_DB_PASSWORD
CREATE ROLE __ROLE__ WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
    NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD :'app_password';
\unset app_password
GRANT CONNECT ON DATABASE __DATABASE__ TO __ROLE__;
GRANT USAGE ON SCHEMA public TO __ROLE__;
GRANT __GRANTS__ ON TABLE public.__TABLE__ TO __ROLE__;
GRANT USAGE ON SEQUENCE public.__TABLE___id_seq TO __ROLE__;
'@

$VerifySqlTemplate = @'
\set ON_ERROR_STOP on
SELECT current_database() AS banco, current_user AS usuario,
       ssl, version AS tls
FROM pg_stat_ssl WHERE pid = pg_backend_pid();
SELECT '__TABLE__' AS tabela, count(*) AS registros FROM public.__TABLE__;
SELECT has_table_privilege(current_user, 'public.__TABLE__', 'SELECT') AS pode_ler,
       has_table_privilege(current_user, 'public.__TABLE__', 'INSERT') AS pode_inserir,
       has_table_privilege(current_user, 'public.__TABLE__', 'UPDATE') AS pode_atualizar,
       has_table_privilege(current_user, 'public.__TABLE__', 'DELETE') AS pode_excluir,
       has_schema_privilege(current_user, 'public', 'CREATE') AS pode_criar_tabelas;
SELECT 1 / CASE WHEN
    current_user = '__ROLE__'
    AND current_database() = '__DATABASE__'
    AND has_database_privilege(current_user, current_database(), 'CONNECT')
    AND has_schema_privilege(current_user, 'public', 'USAGE')
    AND NOT has_schema_privilege(current_user, 'public', 'CREATE')
    AND has_table_privilege(current_user, 'public.__TABLE__', 'SELECT')
    AND has_table_privilege(current_user, 'public.__TABLE__', 'INSERT')
    AND has_table_privilege(current_user, 'public.__TABLE__', 'UPDATE') = __CAN_MODIFY__
    AND has_table_privilege(current_user, 'public.__TABLE__', 'DELETE') = __CAN_MODIFY__
    AND NOT has_table_privilege(current_user, 'public.__TABLE__', 'TRUNCATE')
    AND has_sequence_privilege(current_user, 'public.__TABLE___id_seq', 'USAGE')
    AND EXISTS (SELECT 1 FROM pg_stat_ssl WHERE pid = pg_backend_pid() AND ssl)
    AND NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = current_user
                    AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
    AND NOT EXISTS (SELECT 1 FROM pg_auth_members
                    WHERE member = (SELECT oid FROM pg_roles WHERE rolname = current_user))
    THEN 1 ELSE 0 END AS permissoes_ok;
'@

$JobCommand = @'
psql -X -w --set=ON_ERROR_STOP=1 --single-transaction --file=/scripts/create.sql
PGUSER="$APP_DB_USER" PGPASSWORD="$APP_DB_PASSWORD" \
    psql -X -w --set=ON_ERROR_STOP=1 --single-transaction --file=/scripts/verify.sql
'@

$PlannedResources = @()
$JobNames = @()
$Rng = [Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $Ca = Invoke-KubeRead -KubeArguments @('get', 'configmap', 'rds-ca', '-n', $Namespace, '-o', 'json')
    if ($null -eq $Ca -or $null -eq $Ca.data.PSObject.Properties['global-bundle.pem']) {
        throw 'ConfigMap rds-ca sem global-bundle.pem.'
    }

    # Toda a pre-validacao ocorre antes de criar qualquer recurso.
    foreach ($Db in $Databases) {
        $AdminName = "$($Db.Service)-db-admin"
        $AppName = "$($Db.Service)-db-app"
        $JobName = "$($Db.Service)-db-app-init"
        $SqlName = "$JobName-sql"

        foreach ($Target in @(
            @{ Kind = 'secret'; Name = $AppName },
            @{ Kind = 'configmap'; Name = $SqlName },
            @{ Kind = 'job'; Name = $JobName }
        )) {
            $Existing = Invoke-KubeRead -KubeArguments @('get', $Target.Kind, $Target.Name, '-n', $Namespace, '--ignore-not-found', '-o', 'json')
            if ($null -ne $Existing) {
                throw "Alvo existente: $($Target.Kind)/$($Target.Name). Nao sera sobrescrito. Envie o estado antes de continuar."
            }
        }

        $InitJob = Invoke-KubeRead -KubeArguments @('get', 'job', "$($Db.Service)-db-init", '-n', $Namespace, '-o', 'json')
        if (@($InitJob.status.conditions | Where-Object { $_.type -eq 'Complete' -and $_.status -eq 'True' }).Count -eq 0) {
            throw "A inicializacao de $($Db.Service) ainda nao esta completa."
        }

        $Admin = Invoke-KubeRead -KubeArguments @('get', 'secret', $AdminName, '-n', $Namespace, '-o', 'json')
        $DbHost = Read-SecretField -Secret $Admin -Field 'PGHOST'
        $DbPort = Read-SecretField -Secret $Admin -Field 'PGPORT'
        $DbName = Read-SecretField -Secret $Admin -Field 'PGDATABASE'
        $AdminUser = Read-SecretField -Secret $Admin -Field 'PGUSER'
        $AdminPassword = Read-SecretField -Secret $Admin -Field 'PGPASSWORD'
        if ($DbName -ne $Db.Database -or $DbPort -ne '5432' -or
            $DbHost -notmatch '^[a-zA-Z0-9.-]+\.us-east-1\.rds\.amazonaws\.com$' -or
            [string]::IsNullOrWhiteSpace($AdminUser) -or [string]::IsNullOrWhiteSpace($AdminPassword)) {
            throw "Configuracao inesperada em $AdminName. Nenhum dado sensivel sera exibido."
        }
        $Admin = $null
        $AdminPassword = $null

        $RandomBytes = New-Object byte[] 24
        $Rng.GetBytes($RandomBytes)
        $AppPassword = [BitConverter]::ToString($RandomBytes).Replace('-', '').ToLowerInvariant()
        $DatabaseUrl = 'postgresql://{0}:{1}@{2}:{3}/{4}?sslmode=verify-full&sslrootcert=%2Fetc%2Frds-ca%2Fglobal-bundle.pem&connect_timeout=10' -f `
            $Db.Role, $AppPassword, $DbHost, $DbPort, $DbName
        $SecretValues = @{
            PGHOST = $DbHost; PGPORT = $DbPort; PGDATABASE = $DbName
            PGUSER = $Db.Role; PGPASSWORD = $AppPassword
            PGSSLMODE = 'verify-full'; PGSSLROOTCERT = '/etc/rds-ca/global-bundle.pem'
            DATABASE_URL = $DatabaseUrl
        }
        $EncodedData = @{}
        foreach ($Key in $SecretValues.Keys) {
            $EncodedData[$Key] = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes([string]$SecretValues[$Key]))
        }
        $AppSecret = @{ apiVersion = 'v1'; kind = 'Secret'; metadata = (Get-ObjectMetadata $AppName); type = 'Opaque'; data = $EncodedData }

        $CreateSql = $CreateSqlTemplate.Replace('__ROLE__', $Db.Role).Replace('__DATABASE__', $Db.Database).Replace('__TABLE__', $Db.Table).Replace('__GRANTS__', $Db.Grants)
        $VerifySql = $VerifySqlTemplate.Replace('__ROLE__', $Db.Role).Replace('__DATABASE__', $Db.Database).Replace('__TABLE__', $Db.Table).Replace('__CAN_MODIFY__', $Db.CanModify)
        $SqlConfig = @{
            apiVersion = 'v1'; kind = 'ConfigMap'; metadata = (Get-ObjectMetadata $SqlName)
            data = @{ 'create.sql' = $CreateSql; 'verify.sql' = $VerifySql }
        }
        $Job = @{
            apiVersion = 'batch/v1'; kind = 'Job'; metadata = (Get-ObjectMetadata $JobName)
            spec = @{
                backoffLimit = 0; activeDeadlineSeconds = 300
                template = @{
                    metadata = @{ labels = @{ 'app.kubernetes.io/part-of' = 'togglemaster'; 'app.kubernetes.io/component' = 'db-app-bootstrap' } }
                    spec = @{
                        restartPolicy = 'Never'; automountServiceAccountToken = $false; enableServiceLinks = $false
                        securityContext = @{ runAsNonRoot = $true; runAsUser = 70; runAsGroup = 70; seccompProfile = @{ type = 'RuntimeDefault' } }
                        containers = @(@{
                            name = 'psql'; image = 'postgres:16-alpine'; imagePullPolicy = 'IfNotPresent'
                            command = @('/bin/sh'); args = @('-ec', $JobCommand)
                            envFrom = @(@{ secretRef = @{ name = $AdminName } })
                            env = @(
                                @{ name = 'APP_DB_USER'; valueFrom = @{ secretKeyRef = @{ name = $AppName; key = 'PGUSER' } } },
                                @{ name = 'APP_DB_PASSWORD'; valueFrom = @{ secretKeyRef = @{ name = $AppName; key = 'PGPASSWORD' } } },
                                @{ name = 'PGSSLMODE'; value = 'verify-full' },
                                @{ name = 'PGSSLROOTCERT'; value = '/etc/rds-ca/global-bundle.pem' },
                                @{ name = 'PGCONNECT_TIMEOUT'; value = '10' },
                                @{ name = 'PGOPTIONS'; value = '-c statement_timeout=60000 -c lock_timeout=10000' }
                            )
                            resources = @{ requests = @{ cpu = '50m'; memory = '32Mi' }; limits = @{ cpu = '250m'; memory = '128Mi' } }
                            securityContext = @{ allowPrivilegeEscalation = $false; readOnlyRootFilesystem = $true; capabilities = @{ drop = @('ALL') } }
                            volumeMounts = @(
                                @{ name = 'sql'; mountPath = '/scripts'; readOnly = $true },
                                @{ name = 'rds-ca'; mountPath = '/etc/rds-ca'; readOnly = $true }
                            )
                        })
                        volumes = @(
                            @{ name = 'sql'; configMap = @{ name = $SqlName } },
                            @{ name = 'rds-ca'; configMap = @{ name = 'rds-ca'; items = @(@{ key = 'global-bundle.pem'; path = 'global-bundle.pem' }) } }
                        )
                    }
                }
            }
        }
        $PlannedResources += @($SqlConfig, $AppSecret, $Job)
        $JobNames += $JobName
        $SecretValues = $null
        $AppPassword = $null
        $DatabaseUrl = $null
        [Array]::Clear($RandomBytes, 0, $RandomBytes.Length)
        Write-Host "Preparado: $($Db.Service), usuario $($Db.Role), tabela $($Db.Table)."
    }

    foreach ($Resource in $PlannedResources) { Submit-KubeCreate -Resource $Resource -DryRun }
    if ($ValidateOnly) {
        Write-Host 'Validacao no servidor concluida. Nenhum recurso persistido; senhas temporarias descartadas.'
        return
    }
    foreach ($Resource in $PlannedResources) { Submit-KubeCreate -Resource $Resource }

    $JobRefs = @($JobNames | ForEach-Object { "job/$_" })
    & kubectl --context $EksContext wait -n $Namespace '--for=condition=complete' '--timeout=360s' @JobRefs
    $AllCompleted = ($LASTEXITCODE -eq 0)
    & kubectl --context $EksContext get -n $Namespace @JobRefs
    & kubectl --context $EksContext get pods -n $Namespace -l 'app.kubernetes.io/component=db-app-bootstrap'
    foreach ($JobName in $JobNames) {
        Write-Host "RESULTADO: $JobName"
        & kubectl --context $EksContext logs "job/$JobName" -n $Namespace '--tail=100'
    }
    if (-not $AllCompleted) {
        throw 'Algum Job falhou. Nao exclua Secrets nem repita o script: envie os resultados para diagnostico.'
    }
    Write-Host 'Usuarios de aplicacao criados e conexoes/permissoes verificadas. Nenhum Deployment foi criado.'
}
finally {
    $Rng.Dispose()
    $PlannedResources = $null
    $AppSecret = $null
    $EncodedData = $null
    $SecretValues = $null
    $Admin = $null
    $AdminPassword = $null
    $AppPassword = $null
    $DatabaseUrl = $null
    $Resource = $null
}
