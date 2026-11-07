# make_local_ca.ps1
# ---------------------------------------------------------------------------
# Regenerate the local TLS material with the SAN set the client actually
# expects (three-domain SAN, same as the proven third-party launcher).
#
# Output files (overwritten, keep the old names so fake_auth_tls.py needs no
# change apart from the port):
#   _ca.pem       root CA certificate, PEM
#   _ca.cer       root CA certificate, DER
#   _leaf2.cer    leaf certificate, DER   (SAN = localhost + formal-zone-*)
#   _rsa.txt      leaf RSA private key parameters (base64, one per line)
#
# Side effects:
#   * root CA imported into Cert:\LocalMachine\Root
#
# NOTE: this script is ASCII-only on purpose (PowerShell 5.1 reads BOM-less
# files as GBK, which mangles non-ASCII paths). The game directory path
# contains non-ASCII characters, so cacert.pem is NOT touched here -- the
# caller (run_all.py, i.e. Python) appends _ca.pem to it instead.
# ---------------------------------------------------------------------------
param(
    [string]$Root = 'e:\codol tae'
)

$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path -LiteralPath $Root).Path
$names = @('localhost',
           'formal-zone-auth.codol.qq.com',
           'formal-zone-lsg.codol.qq.com')

Write-Host "=== make_local_ca ===" -ForegroundColor Cyan
Write-Host ("  output dir : " + $Root)
Write-Host ("  SAN        : " + ($names -join ', '))

# ---- 0) drop previous local CAs so the Root store does not pile up -------
foreach ($store in @('Cert:\LocalMachine\My', 'Cert:\LocalMachine\Root')) {
    Get-ChildItem $store -ErrorAction SilentlyContinue |
        Where-Object { $_.Subject -like 'CN=CODOL Local*' -or $_.Subject -like 'CN=CODOL-LOCAL-CA*' } |
        ForEach-Object {
            $t = $_.Thumbprint
            try { Remove-Item -LiteralPath $_.PSPath -Force -ErrorAction Stop
                  Write-Host ("    removed old cert " + $t + " from " + $store) } catch { }
        }
}

# ---- 1) root CA ----------------------------------------------------------
$sid = [Guid]::NewGuid().ToString('N').Substring(0, 8)
$caSubject = 'CN=CODOL Local CA ' + $sid
Write-Host ("[*] creating root CA: " + $caSubject)

$ca = New-SelfSignedCertificate `
        -Type Custom `
        -Subject $caSubject `
        -CertStoreLocation 'Cert:\LocalMachine\My' `
        -KeyAlgorithm RSA -KeyLength 2048 -HashAlgorithm SHA256 `
        -KeyUsage CertSign, CRLSign, DigitalSignature `
        -TextExtension @('2.5.29.19={critical}{text}ca=1&pathlength=0') `
        -NotAfter (Get-Date).AddDays(30) `
        -FriendlyName ('CODOL Local CA ' + $sid)

Write-Host ("    thumbprint = " + $ca.Thumbprint)

$caDer = Join-Path $Root '_ca.cer'
$caPem = Join-Path $Root '_ca.pem'
Export-Certificate -Cert $ca -FilePath $caDer -Type CERT | Out-Null

$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($caDer))
$b64lines = ([regex]::Matches($b64, '.{1,64}') | ForEach-Object { $_.Value }) -join "`n"
$pemText = "-----BEGIN CERTIFICATE-----`n" + $b64lines + "`n-----END CERTIFICATE-----`n"
[IO.File]::WriteAllBytes($caPem, [Text.Encoding]::ASCII.GetBytes($pemText))
Write-Host ("    wrote " + $caPem)

# make it a trust anchor
Import-Certificate -FilePath $caDer -CertStoreLocation 'Cert:\LocalMachine\Root' | Out-Null
Write-Host "    imported into LocalMachine\Root"

# ---- 2) leaf key (must be exportable so we can build a PEM by hand) -------
$rsa = [System.Security.Cryptography.RSA]::Create(2048)
$rsaTxt = Join-Path $Root '_rsa.txt'
$p = $rsa.ExportParameters($true)
$lines = foreach ($n in @('Modulus','Exponent','D','P','Q','DP','DQ','InverseQ')) {
    $n + '=' + [Convert]::ToBase64String($p.$n)
}
[IO.File]::WriteAllBytes($rsaTxt, [Text.Encoding]::ASCII.GetBytes(($lines -join "`n") + "`n"))
Write-Host ("    wrote " + $rsaTxt)

# ---- 3) leaf certificate, signed by the root -----------------------------
Write-Host ("[*] creating leaf for: " + ($names -join ', '))
$req = New-Object System.Security.Cryptography.X509Certificates.CertificateRequest(
            ('CN=' + $names[1]),
            $rsa,
            [System.Security.Cryptography.HashAlgorithmName]::SHA256,
            [System.Security.Cryptography.RSASignaturePadding]::Pkcs1)

$san = New-Object System.Security.Cryptography.X509Certificates.SubjectAlternativeNameBuilder
foreach ($n in $names) { $san.AddDnsName($n) }
$req.CertificateExtensions.Add($san.Build())

$ekuOids = New-Object System.Security.Cryptography.OidCollection
$null = $ekuOids.Add((New-Object System.Security.Cryptography.Oid('1.3.6.1.5.5.7.3.1')))   # serverAuth
$req.CertificateExtensions.Add(
    (New-Object System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension($ekuOids, $false)))

$ku = [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature -bor `
      [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::KeyEncipherment
$req.CertificateExtensions.Add(
    (New-Object System.Security.Cryptography.X509Certificates.X509KeyUsageExtension($ku, $true)))

$req.CertificateExtensions.Add(
    (New-Object System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension($false, $false, 0, $true)))

$serial = New-Object byte[] 8
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($serial)
$serial[0] = $serial[0] -band 0x7F

$caCert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($ca)
# notAfter must not exceed the issuer's; reuse the CA's own bounds.
$leaf = $req.Create($caCert,
                    $caCert.NotBefore,
                    $caCert.NotAfter,
                    $serial)
# NOTE: do NOT call CopyWithPrivateKey here -- it is an extension method and
# PowerShell cannot invoke it directly. We do not need it anyway: the public
# certificate goes to _leaf2.cer and the private key to _rsa.txt separately,
# and fake_auth_tls.py recombines them into PEM.

$leafDer = Join-Path $Root '_leaf2.cer'
[IO.File]::WriteAllBytes($leafDer, $leaf.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert))
Write-Host ("    wrote " + $leafDer + "  (subject=" + $leaf.Subject + ")")

# ---- 4) summary ----------------------------------------------------------
Write-Host ""
Write-Host "=== done ===" -ForegroundColor Green
Write-Host ("  _ca.pem    " + (Get-Item $caPem).Length + " bytes")
Write-Host ("  _ca.cer    " + (Get-Item $caDer).Length + " bytes")
Write-Host ("  _leaf2.cer " + (Get-Item $leafDer).Length + " bytes")
Write-Host ("  _rsa.txt   " + (Get-Item $rsaTxt).Length + " bytes")
Write-Host ("  SAN        " + ($names -join ', '))
