[CmdletBinding()]
param(
    [ValidateSet('Status', 'Start', 'Stop', 'Connect', 'AllowCurrentIp')]
    [string]$Action = 'Status'
)

$ErrorActionPreference = 'Stop'
$kltnRoot = Split-Path -Parent $PSScriptRoot
$kltnPython = Join-Path $kltnRoot 'workspace-support/.codex-azure/venv/Scripts/python.exe'
$kltnGroup = 'rg-kltn'
$kltnVm = 'vm-kltn-ubuntu'
$kltnSubscription = '13e2faa3-b3e1-49ce-8db6-a197e8315b25'
$env:AZURE_CONFIG_DIR = Join-Path $env:LOCALAPPDATA 'KLTN-AzureCLI'

if (-not (Test-Path -LiteralPath $kltnPython)) {
    throw 'The project Azure CLI environment is missing.'
}

function Invoke-KltnAz {
    & $kltnPython -m azure.cli @args --subscription $kltnSubscription --only-show-errors
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI failed with exit code $LASTEXITCODE."
    }
}

switch ($Action) {
    'Status' {
        Invoke-KltnAz vm show --resource-group $kltnGroup --name $kltnVm --show-details --query '{name:name,location:location,size:hardwareProfile.vmSize,power:powerState,publicIp:publicIps}' --output json
    }
    'Start' {
        Invoke-KltnAz vm start --resource-group $kltnGroup --name $kltnVm
    }
    'Stop' {
        Invoke-KltnAz vm deallocate --resource-group $kltnGroup --name $kltnVm
    }
    'AllowCurrentIp' {
        $kltnIpJson = & $kltnPython (Join-Path $PSScriptRoot 'Detect-EgressIp.py')
        if ($LASTEXITCODE -ne 0) {
            throw 'Could not verify both HTTP and HTTPS egress routes. SSH access was not changed.'
        }
        $kltnIps = ConvertFrom-Json -InputObject ($kltnIpJson -join [Environment]::NewLine)
        $kltnCidrs = @(foreach ($kltnIp in $kltnIps) { "$kltnIp/32" })
        $kltnUpdateArgs = @('network', 'nsg', 'rule', 'update', '--resource-group', $kltnGroup, '--nsg-name', "$kltnVm-nsg", '--name', 'AllowSshFromResearcher', '--source-address-prefixes') + $kltnCidrs + @('--output', 'none')
        Invoke-KltnAz @kltnUpdateArgs
        Write-Output 'SSH now permits only the verified public IPv4 addresses for this network.'
    }
    'Connect' {
        $kltnPublicIp = ([string](Invoke-KltnAz network public-ip show --resource-group $kltnGroup --name "$kltnVm-ip" --query ipAddress --output tsv)).Trim()
        $kltnKey = Join-Path $env:USERPROFILE '.ssh/kltn_azure_ed25519'
        $kltnKnownHosts = Join-Path $env:USERPROFILE '.ssh/known_hosts_kltn'
        if (-not (Test-Path -LiteralPath $kltnKey) -or -not (Test-Path -LiteralPath $kltnKnownHosts)) {
            throw 'Dedicated SSH key or verified host-key file is missing.'
        }
        & ssh -i $kltnKey -o "UserKnownHostsFile=$kltnKnownHosts" -o StrictHostKeyChecking=yes "azureuser@$kltnPublicIp"
        if ($LASTEXITCODE -ne 0) {
            throw 'SSH failed. Check VM power state and update AllowCurrentIp if your network changed.'
        }
    }
}
