param(
    [Parameter(Mandatory = $true)]
    [string] $Path
)

# Read the one-line selection written by alpha0022/map_handoff.stamp().  The
# values are printed with a delimiter that START-CODOL-SERVER.cmd can consume.
# Treat the handoff as untrusted input: these strings become command-line dvar
# values, so accept only the identifiers the engine itself can name.
try {
    $text = [System.IO.File]::ReadAllText($Path)
} catch {
    exit 1
}

# The lobby publishes one atomic decision. Do not merge fields from another
# record under the first record's fresh timestamp: that can boot a different
# map than the one C1 was told to join. A final Windows/Unix line ending is OK.
if ($text -notmatch '\A[^\r\n]*(?:\r?\n)?\z') {
    exit 1
}

$parts = $text -split '\s+'
if ($parts.Count -lt 4) {
    exit 1
}

$stamp = 0.0
if (-not [double]::TryParse(
        $parts[0],
        [System.Globalization.NumberStyles]::Float,
        [System.Globalization.CultureInfo]::InvariantCulture,
        [ref] $stamp)) {
    exit 1
}

# The stamp is the lobby's Unix time at the Ready press.  A cold start long after
# that press must not replay it: a stale zombies/coop decision would boot the
# server into a map nobody is about to join.  Live dispatch arrives over rcon
# anyway; the file only exists to keep a server started right after Ready in
# step with the client.  Ten minutes covers that window with margin.
$ageSeconds = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - [long][math]::Floor($stamp)
if ($ageSeconds -lt -60 -or $ageSeconds -gt 600) {
    exit 1
}

$values = @{}
foreach ($part in $parts[3..($parts.Count - 1)]) {
    $split = $part.IndexOf('=')
    if ($split -le 0) {
        continue
    }
    $values[$part.Substring(0, $split)] = $part.Substring($split + 1)
}

$map = $values['map']
$zoneType = $values['type']
$gametype = $values['gametype']
# The playlist/session spelling.  Differs from $map only for co-op
# (coop_training_mp_killhouse_sh vs mp_killhouse_sh); map_handoff.stamp() emits
# it for every category, and an older stamp without it falls back to $map.
$sessionMap = $values['session_map']
if (-not $sessionMap) {
    $sessionMap = $map
}
if ($map -notmatch '^[a-z][a-z0-9_]{0,63}$' -or
    $sessionMap -notmatch '^[a-z][a-z0-9_]{0,63}$' -or
    $zoneType -notmatch '^(mp|coop|zm)$' -or
    $gametype -notmatch '^[a-z][a-z0-9_]{0,31}$') {
    exit 1
}

Write-Output ($map + '|' + $gametype + '|' + $zoneType + '|' + $sessionMap)
