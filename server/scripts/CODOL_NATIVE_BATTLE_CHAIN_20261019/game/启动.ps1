$wi=[Security.Principal.WindowsIdentity]::GetCurrent()
$wp=New-Object Security.Principal.WindowsPrincipal($wi)
$wp.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
whoami /groups | findstr "Mandatory Label"
