param(
    [string]$Flutter = 'flutter',
    [string]$AndroidSdk = '',
    [ValidateSet('demo', 'live')][string]$Mode = 'demo',
    [string]$ApiBaseUrl = '',
    [string]$DeviceId = '',
    [switch]$Integration
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$mobile = Join-Path $projectRoot 'apps/mobile'
$qa = Join-Path $projectRoot '.tools/qa'
New-Item -ItemType Directory -Force -Path $qa | Out-Null
$reportPath = Join-Path $projectRoot 'docs/BUILD_STATUS.json'
$result = [ordered]@{ status = 'running'; timestamp_utc = [DateTime]::UtcNow.ToString('o'); mode = $Mode; android_sdk = $AndroidSdk; checks = @(); apk = $null; sha256 = $null; error = $null }
$oldSdk = $env:ANDROID_HOME
$oldLocation = Get-Location
function Invoke-FlutterStep([string]$Name, [string[]]$Arguments) {
    & $Flutter @Arguments 2>&1 | Tee-Object -FilePath (Join-Path $qa "$Name.log")
    if ($LASTEXITCODE -ne 0) { throw "$Name failed with exit code $LASTEXITCODE; see .tools/qa/$Name.log" }
    $result.checks += $Name
}
try {
    if ($Integration -and $Mode -ne 'demo') { throw 'The existing integration suite requires demo mode' }
    Get-Command $Flutter -ErrorAction Stop | Out-Null
    if ($AndroidSdk) {
        $resolvedSdk = (Resolve-Path -LiteralPath $AndroidSdk).Path
        if (-not (Test-Path -LiteralPath (Join-Path $resolvedSdk 'platform-tools/adb.exe'))) { throw 'Android SDK lacks platform-tools/adb.exe' }
        $env:ANDROID_HOME = $resolvedSdk
    }
    if ($Mode -eq 'live') {
        $apiUri = $null
        if (-not [Uri]::TryCreate($ApiBaseUrl, [UriKind]::Absolute, [ref]$apiUri) -or $apiUri.Scheme -notin @('http', 'https')) {
            throw 'Live build requires a valid public API_BASE_URL (never API credentials)'
        }
    }
    & (Join-Path $PSScriptRoot 'bootstrap-mobile.ps1') -Flutter $Flutter
    Set-Location -LiteralPath $mobile
    Invoke-FlutterStep -Name 'version' -Arguments @('--version')
    Invoke-FlutterStep -Name 'pub-get' -Arguments @('pub', 'get')
    Invoke-FlutterStep -Name 'l10n' -Arguments @('gen-l10n')
    Invoke-FlutterStep -Name 'analyze' -Arguments @('analyze')
    Invoke-FlutterStep -Name 'test' -Arguments @('test')
    $demoValue = if ($Mode -eq 'demo') { 'true' } else { 'false' }
    $defines = @("--dart-define=DEMO_MODE=$demoValue")
    if ($Mode -eq 'live') { $defines += "--dart-define=API_BASE_URL=$ApiBaseUrl" }
    if ($Integration) {
        if (-not $DeviceId) { throw 'Integration tests require an explicit emulator/device ID' }
        Invoke-FlutterStep -Name 'integration' -Arguments (@('test', 'integration_test', '-d', $DeviceId) + $defines)
    }
    Invoke-FlutterStep -Name 'apk-debug' -Arguments (@('build', 'apk', '--debug') + $defines)
    $apk = Join-Path $mobile 'build/app/outputs/flutter-apk/app-debug.apk'
    if (-not (Test-Path -LiteralPath $apk)) { throw 'Build did not produce the expected APK' }
    $result.apk = $apk
    $result.sha256 = (Get-FileHash -LiteralPath $apk -Algorithm SHA256).Hash
    $result.status = 'success'
} catch {
    $result.status = 'blocked'
    $result.error = $_.Exception.Message
    throw
} finally {
    $result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding utf8
    $env:ANDROID_HOME = $oldSdk
    Set-Location -LiteralPath $oldLocation.Path
}
