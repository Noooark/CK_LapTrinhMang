param(
    [Parameter(Mandatory)]
    [ValidateSet('Server', 'Client')]
    [string]$Mode,
    [string]$Python = 'py',
    [string]$OpenSsl
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$privateDir = Join-Path $env:LOCALAPPDATA 'CK_LapTrinhMang\EvidenceDemo'
$certificate = Join-Path $privateDir 'localhost.pem'
$key = Join-Path $privateDir 'localhost.key'

if ($Mode -eq 'Server') {
    if (-not (Test-Path -LiteralPath $certificate) -or -not (Test-Path -LiteralPath $key)) {
        if (-not $OpenSsl) {
            $command = Get-Command openssl.exe -ErrorAction SilentlyContinue
            if (-not $command) {
                throw 'Install OpenSSL or pass -OpenSsl with the path to openssl.exe.'
            }
            $OpenSsl = $command.Source
        }
        New-Item -ItemType Directory -Force -Path $privateDir | Out-Null
        $requestConfig = Join-Path $privateDir 'openssl.cnf'
        @'
[req]
distinguished_name = dn
[dn]
CN = localhost
'@ | Set-Content -LiteralPath $requestConfig -Encoding ascii
        & $OpenSsl req -x509 -newkey rsa:2048 -nodes -days 365 -config $requestConfig `
            -subj '/CN=localhost' -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1' `
            -out $certificate -keyout $key
        if ($LASTEXITCODE -ne 0) {
            throw 'OpenSSL could not create the local TLS certificate.'
        }
    }
} elseif (-not (Test-Path -LiteralPath $certificate)) {
    throw 'Start the local TLS Server once before launching a Client.'
}

Push-Location -LiteralPath $repo
try {
    if ($Mode -eq 'Server') {
        $env:QUIZ_TLS_CERT = $certificate
        $env:QUIZ_TLS_KEY = $key
        $env:QUIZ_SNAPSHOT_DIR = Join-Path $privateDir 'snapshots'
        & $Python -c "from server.main import QuizServer, load_config, tls_context_from_env, SnapshotService; config = load_config(); config['host'] = '127.0.0.1'; QuizServer(**config, tls_context=tls_context_from_env(), snapshots=SnapshotService.from_env()).start()"
    } else {
        $env:QUIZ_TLS_CA = $certificate
        & $Python -c "import sys; from client.main import main; from client.network import ServerConnection; main() if ServerConnection().host in ('localhost', '127.0.0.1') else sys.exit('Set client server_host to 127.0.0.1 for the local demo')"
    }
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
