param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 65535)]
    [int] $Port
)

$ErrorActionPreference = 'Stop'
try {
    $owners = @(Get-NetUDPEndpoint -ErrorAction Stop |
        Where-Object { $_.LocalPort -eq $Port } |
        Select-Object -ExpandProperty OwningProcess -Unique)
} catch {
    Write-Error "Cannot check UDP/$Port before starting the dedicated server: $($_.Exception.Message)"
    exit 2
}

if ($owners.Count -gt 0) {
    Write-Host "UDP/$Port is already owned by PID $($owners -join ', '); leave that server running or stop it deliberately before restarting."
    exit 1
}

exit 0
