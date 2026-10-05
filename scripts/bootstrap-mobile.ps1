param([string]$Flutter = 'flutter')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$mobile = Join-Path $projectRoot 'apps/mobile'
if (Test-Path -LiteralPath (Join-Path $mobile 'android')) {
    Write-Host 'Android scaffold exists; preserving existing files.'
    return
}
Get-Command $Flutter -ErrorAction Stop | Out-Null
$staging = Join-Path $projectRoot ('.tools/android-scaffold-' + [guid]::NewGuid().ToString('N'))
& $Flutter create --platforms=android --org ir.nabzcoin --project-name nabz_coin --no-pub $staging
if ($LASTEXITCODE -ne 0) { throw 'Flutter create failed; source files were preserved.' }
Copy-Item -LiteralPath (Join-Path $staging 'android') -Destination $mobile -Recurse
$manifest = Join-Path $mobile 'android/app/src/main/AndroidManifest.xml'
$text = Get-Content -LiteralPath $manifest -Raw
$text = $text.Replace('android:label="nabz_coin"', 'android:label="نبض کوین"')
$text = $text.Replace('<application', '<uses-permission android:name="android.permission.INTERNET"/><application')
Set-Content -LiteralPath $manifest -Value $text -Encoding utf8
$debugManifest = Join-Path $mobile 'android/app/src/debug/AndroidManifest.xml'
$debugText = Get-Content -LiteralPath $debugManifest -Raw
$debugText = $debugText.Replace('</manifest>', '<application android:usesCleartextTraffic="true"/></manifest>')
Set-Content -LiteralPath $debugManifest -Value $debugText -Encoding utf8
Write-Host 'Android scaffold generated. Original Dart/pubspec/assets were preserved. Debug allows local HTTP; release requires HTTPS.'
