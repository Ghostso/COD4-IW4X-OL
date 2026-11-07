$sbx = 'D:\BAIDUN~1\使命召~1\RUN_CO~1\SANDBO~4'
$adPath = "$sbx\WeGameLauncher\game\ad_login.png"
$adVideo = "$sbx\WeGameLauncher\game\ad_mini.mp4"
$json = '{"ad_begin":"","ad_end":"","ad_path":"' + $adPath.Replace('\','\\') + '","ad_type":1,"ad_url":"http://codol.qq.com/","ad_video":"' + $adVideo.Replace('\','\\') + '","click_btn_show_txt":"查看详情","custom":"26","game_id":29,"launcher_ver":"1.3.0.76"}'
$arguments = '-launcher=' + $json + ' StartFor=29 AddPath="' + $sbx + '"'

Write-Host "SBX:" $sbx
Write-Host "Arguments:" $arguments

$exe = "$sbx\codoMP_client_shipRetail.exe"
Write-Host "EXE:" $exe

cmd /c start "CODOL Test" /d "$sbx" "$exe" $arguments
Write-Host "Launched via cmd"