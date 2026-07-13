param(
    [string]$EnvPath = (Join-Path $PSScriptRoot '.env')
)

function Read-PlainSecret {
    param([string]$Prompt)

    $secure = Read-Host -Prompt $Prompt -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

$supabaseUrl = Read-Host -Prompt 'Supabase Project URL'
if ([string]::IsNullOrWhiteSpace($supabaseUrl)) {
    throw 'Supabase Project URL cannot be empty.'
}

$serviceRoleKey = Read-PlainSecret -Prompt 'Supabase secret or service_role key'
if ([string]::IsNullOrWhiteSpace($serviceRoleKey)) {
    throw 'Supabase key cannot be empty.'
}

$memoryToken = [Guid]::NewGuid().ToString('N') + [Guid]::NewGuid().ToString('N')
$content = @(
    "SUPABASE_URL=$supabaseUrl",
    "SUPABASE_SERVICE_ROLE_KEY=$serviceRoleKey",
    "MEMORY_API_TOKEN=$memoryToken"
) -join [Environment]::NewLine

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($EnvPath, $content, $utf8NoBom)

Write-Host ''
Write-Host 'Created .env successfully. The Supabase key was not displayed.' -ForegroundColor Green
Write-Host 'Memory API token (copy it for later Dify configuration):' -ForegroundColor Yellow
Write-Host $memoryToken -ForegroundColor Yellow
