param(
    [Parameter(Mandatory=$true)][string]$OutPng
)
Add-Type -AssemblyName System.Drawing,System.Windows.Forms
$b = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.Left, $b.Top, 0, 0, $bmp.Size)
$bmp.Save($OutPng, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
Write-Output ("SAVED {0}x{1} -> {2}" -f $b.Width, $b.Height, $OutPng)
