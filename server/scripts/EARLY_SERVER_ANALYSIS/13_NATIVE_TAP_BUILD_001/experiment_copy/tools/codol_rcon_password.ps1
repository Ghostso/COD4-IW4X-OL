param(
    [Parameter(Mandatory = $true)]
    [string] $Path
)

$ErrorActionPreference = 'Stop'

try {
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $directory = [System.IO.Path]::GetDirectoryName($fullPath)
    if (-not [System.IO.Directory]::Exists($directory)) {
        throw 'Lobby state directory does not exist.'
    }

    if (-not [System.IO.File]::Exists($fullPath)) {
        $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try {
            $bytes = New-Object byte[] 16
            $random.GetBytes($bytes)
            $password = [System.BitConverter]::ToString($bytes).Replace('-', '').ToLowerInvariant()
        } finally {
            $random.Dispose()
        }
        try {
            # CreateNew prevents concurrent launcher instances from replacing
            # the password another instance has already given to the lobby.
            $file = [System.IO.File]::Open($fullPath, [System.IO.FileMode]::CreateNew,
                [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
            try {
                $encoded = [System.Text.Encoding]::ASCII.GetBytes($password)
                $file.Write($encoded, 0, $encoded.Length)
            } finally {
                $file.Dispose()
            }
        } catch [System.IO.IOException] {
            if (-not [System.IO.File]::Exists($fullPath)) { throw }
        }
    }

    # Existing credentials are accepted when they can safely become one
    # quoted +set argument. Do not echo the credential into logs or console.
    $valid = $false
    for ($attempt = 0; $attempt -lt 20; ++$attempt) {
        try {
            $value = [System.IO.File]::ReadAllText($fullPath, [System.Text.Encoding]::ASCII)
            if ($value -match '^[A-Za-z0-9_-]{1,128}\r?\n?$') {
                $valid = $true
                break
            }
        } catch [System.IO.IOException] {
            # A second launcher may still be writing its CreateNew file.
        }
        Start-Sleep -Milliseconds 50
    }
    if (-not $valid) { throw 'RCON credential is empty, unreadable, or contains unsafe characters.' }
} catch {
    [Console]::Error.WriteLine('Could not prepare native_server_rcon.txt: ' + $_.Exception.Message)
    exit 1
}
