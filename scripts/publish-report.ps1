#Requires -Version 7.5

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)]
    [string] $ReportPath,

    [string] $RepositoryRoot = (Split-Path -Parent $PSScriptRoot),

    [string] $Remote = 'origin',

    [string] $Branch = 'reports',

    [switch] $NoPush,

    [switch] $SkipDeploymentTrigger
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Invoke-Git {
    param(
        [Parameter(Mandatory)]
        [string] $WorkingDirectory,

        [Parameter(ValueFromRemainingArguments)]
        [string[]] $Arguments
    )

    $output = & git -C $WorkingDirectory @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed: $($output -join [Environment]::NewLine)"
    }

    return $output
}

function Get-PropertyValue {
    param(
        [AllowNull()]
        [object] $Object,

        [Parameter(Mandatory)]
        [string] $Name
    )

    if ($null -eq $Object) {
        return $null
    }

    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        return $null
    }

    return $property.Value
}

function Assert-ValidatedReport {
    param(
        [Parameter(Mandatory)]
        [object] $Report,

        [Parameter(Mandatory)]
        [string] $RawJson
    )

    $metadata = Get-PropertyValue -Object $Report -Name 'metadata'
    $marketDateValue = Get-PropertyValue -Object $metadata -Name 'marketDate'
    if ([string]::IsNullOrWhiteSpace([string] $marketDateValue)) {
        throw 'The report must contain metadata.marketDate.'
    }

    $parsedDate = [DateTime]::MinValue
    if (-not [DateTime]::TryParseExact(
        [string] $marketDateValue,
        'yyyy-MM-dd',
        [Globalization.CultureInfo]::InvariantCulture,
        [Globalization.DateTimeStyles]::None,
        [ref] $parsedDate
    )) {
        throw 'metadata.marketDate must use YYYY-MM-DD format.'
    }

    $qa = Get-PropertyValue -Object $Report -Name 'qa'
    if ($null -eq $qa) {
        throw 'The report must contain an explicit qa result.'
    }

    $publishable = Get-PropertyValue -Object $qa -Name 'publishable'
    if ($publishable -ne $true) {
        throw 'The report must contain qa.publishable=true.'
    }

    $movers = @(Get-PropertyValue -Object $Report -Name 'movers')
    if ($movers.Count -ne 20) {
        throw 'The report must contain exactly 20 movers.'
    }
    if (@($movers | Where-Object { (Get-PropertyValue -Object $_ -Name 'direction') -eq 'gainer' }).Count -ne 10 -or
        @($movers | Where-Object { (Get-PropertyValue -Object $_ -Name 'direction') -eq 'loser' }).Count -ne 10) {
        throw 'The report must contain exactly 10 gainers and 10 losers.'
    }
    if (@($movers | Where-Object { (Get-PropertyValue -Object $_ -Name 'deepDive') -eq $true }).Count -ne 6) {
        throw 'The report must identify exactly 6 deep-dive movers.'
    }

    $themes = @(Get-PropertyValue -Object $Report -Name 'themes')
    if ($themes.Count -gt 3) {
        throw 'The report may contain at most 3 themes.'
    }

    $marketEtfs = @(Get-PropertyValue -Object $Report -Name 'marketEtfs')
    if ($marketEtfs.Count -lt 4) {
        throw 'The report must contain SPY, QQQ, DIA, and IWM market data.'
    }

    $statuses = Get-PropertyValue -Object $qa -Name 'reviewerStatuses'
    if ((Get-PropertyValue -Object $statuses -Name 'fact_checker') -ne 'pass') {
        throw 'fact_checker must pass before publication.'
    }
    foreach ($reviewer in @('blog_quality_reviewer', 'humanify_reviewer')) {
        if ((Get-PropertyValue -Object $statuses -Name $reviewer) -eq 'block') {
            throw "$reviewer blocks publication."
        }
    }

    $sources = @(Get-PropertyValue -Object $Report -Name 'sources')
    $sourceIds = @($sources | ForEach-Object { [string] (Get-PropertyValue -Object $_ -Name 'sourceId') })
    foreach ($source in $sources) {
        $sourceUrl = [string] (Get-PropertyValue -Object $source -Name 'url')
        $parsedUrl = $null
        if (-not [Uri]::TryCreate($sourceUrl, [UriKind]::Absolute, [ref] $parsedUrl) -or $parsedUrl.Scheme -ne 'https') {
            throw "Every published source must use a valid HTTPS URL: $sourceUrl"
        }
    }
    foreach ($sourceId in @(Get-PropertyValue -Object $Report -Name 'sourceIds')) {
        if ([string] $sourceId -notin $sourceIds) {
            throw "The report references an unknown sourceId: $sourceId"
        }
    }

    $secretPatterns = [ordered]@{
        'Alpaca API key variable' = '(?i)(APCA_API_KEY_ID|APCA_API_SECRET_KEY|ALPACA_API_KEY)\s*[=:]\s*["'']?[^\s,"'']+'
        'GitHub token' = '(?i)(ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})'
        'AWS access key' = '(?i)AKIA[0-9A-Z]{16}'
        'Private key' = '-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'
    }

    foreach ($entry in $secretPatterns.GetEnumerator()) {
        if ($RawJson -match $entry.Value) {
            throw "Potential secret detected ($($entry.Key)); publication stopped."
        }
    }

    return [string] $marketDateValue
}

function Get-GitHubRepositorySlug {
    param(
        [Parameter(Mandatory)]
        [string] $RemoteUrl
    )

    if ($RemoteUrl -match '^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)(?<slug>[^/\s]+/[^/\s]+?)(?:\.git)?$') {
        return $Matches.slug
    }

    return $null
}

function Request-PagesDeployment {
    param(
        [Parameter(Mandatory)]
        [string] $RemoteUrl
    )

    $repositorySlug = Get-GitHubRepositorySlug -RemoteUrl $RemoteUrl
    if ([string]::IsNullOrWhiteSpace($repositorySlug)) {
        Write-Verbose 'The remote is not hosted on GitHub; skipping Pages workflow dispatch.'
        return
    }

    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Write-Warning 'The report was pushed, but GitHub CLI is unavailable. Run the Deploy GitHub Pages workflow manually.'
        return
    }

    $dispatchOutput = & gh workflow run deploy-pages.yml --ref main --repo $repositorySlug 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "The report was pushed, but Pages workflow dispatch failed: $($dispatchOutput -join [Environment]::NewLine)"
        return
    }

    Write-Output 'Requested the Deploy GitHub Pages workflow on main.'
}

$resolvedRepository = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$resolvedReport = (Resolve-Path -LiteralPath $ReportPath).Path

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'git is required but was not found on PATH.'
}

$insideWorkTree = (Invoke-Git -WorkingDirectory $resolvedRepository rev-parse --is-inside-work-tree) -join ''
if ($insideWorkTree.Trim() -ne 'true') {
    throw "RepositoryRoot is not a Git worktree: $resolvedRepository"
}

$rawJson = [IO.File]::ReadAllText($resolvedReport, [Text.Encoding]::UTF8)
try {
    $report = $rawJson | ConvertFrom-Json -Depth 100 -DateKind String
}
catch {
    throw "Report is not valid JSON: $($_.Exception.Message)"
}

$marketDate = Assert-ValidatedReport -Report $report -RawJson $rawJson
$contentHash = (Get-FileHash -LiteralPath $resolvedReport -Algorithm SHA256).Hash.ToLowerInvariant()
$publishedAt = [DateTimeOffset]::UtcNow.ToString('o')
$temporaryDirectory = Join-Path ([IO.Path]::GetTempPath()) ("stocks-tracker-publish-{0}" -f [Guid]::NewGuid().ToString('N'))

try {
    New-Item -ItemType Directory -Path $temporaryDirectory | Out-Null
    Invoke-Git -WorkingDirectory $resolvedRepository clone --quiet --no-checkout . $temporaryDirectory | Out-Null

    $remoteUrl = (Invoke-Git -WorkingDirectory $resolvedRepository remote get-url $Remote) -join ''
    Invoke-Git -WorkingDirectory $temporaryDirectory remote set-url origin $remoteUrl.Trim() | Out-Null

    & git -C $temporaryDirectory ls-remote --exit-code --heads origin $Branch *> $null
    $remoteBranchExists = $LASTEXITCODE -eq 0

    if ($remoteBranchExists) {
        Invoke-Git -WorkingDirectory $temporaryDirectory fetch --quiet --depth=1 origin $Branch | Out-Null
        Invoke-Git -WorkingDirectory $temporaryDirectory checkout --quiet -B $Branch FETCH_HEAD | Out-Null
    }
    else {
        Invoke-Git -WorkingDirectory $temporaryDirectory checkout --quiet --orphan $Branch | Out-Null
        & git -C $temporaryDirectory rm -r --force --ignore-unmatch . *> $null
        Get-ChildItem -LiteralPath $temporaryDirectory -Force |
            Where-Object Name -ne '.git' |
            Remove-Item -Recurse -Force
    }

    $reportsDirectory = Join-Path $temporaryDirectory 'reports'
    New-Item -ItemType Directory -Path $reportsDirectory -Force | Out-Null
    $destination = Join-Path $reportsDirectory "$marketDate.json"

    if (Test-Path -LiteralPath $destination) {
        $existingHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($existingHash -eq $contentHash) {
            Write-Output "Report $marketDate is already published with identical content."
            return
        }
    }

    Copy-Item -LiteralPath $resolvedReport -Destination $destination -Force

    $indexPath = Join-Path $temporaryDirectory 'index.json'
    $entries = @()
    if (Test-Path -LiteralPath $indexPath) {
        try {
            $existingIndex = Get-Content -LiteralPath $indexPath -Raw | ConvertFrom-Json -Depth 100 -DateKind String
            $existingEntries = Get-PropertyValue -Object $existingIndex -Name 'reports'
            if ($null -ne $existingEntries) {
                $entries = @($existingEntries | Where-Object { $_.marketDate -ne $marketDate })
            }
        }
        catch {
            throw "Existing reports index is invalid JSON: $($_.Exception.Message)"
        }
    }

    $entries += [pscustomobject]@{
        marketDate = $marketDate
        path = "reports/$marketDate.json"
        sha256 = $contentHash
        publishedAt = $publishedAt
    }
    $entries = @($entries | Sort-Object marketDate -Descending)

    $index = [ordered]@{
        generatedAt = $publishedAt
        latestMarketDate = $entries[0].marketDate
        reports = $entries
    }
    $indexJson = $index | ConvertTo-Json -Depth 20
    [IO.File]::WriteAllText($indexPath, "$indexJson`n", [Text.UTF8Encoding]::new($false))

    Invoke-Git -WorkingDirectory $temporaryDirectory add -- index.json "reports/$marketDate.json" | Out-Null
    & git -C $temporaryDirectory diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Output 'No publication changes were detected.'
        return
    }

    Invoke-Git -WorkingDirectory $temporaryDirectory config user.name 'github-actions[bot]' | Out-Null
    Invoke-Git -WorkingDirectory $temporaryDirectory config user.email '41898282+github-actions[bot]@users.noreply.github.com' | Out-Null

    if ($PSCmdlet.ShouldProcess("$Remote/$Branch", "Publish validated report for $marketDate")) {
        Invoke-Git -WorkingDirectory $temporaryDirectory commit --quiet -m "reports: publish $marketDate" | Out-Null
        if ($NoPush) {
            Write-Output "Created publication commit for $marketDate (push skipped)."
        }
        else {
            Invoke-Git -WorkingDirectory $temporaryDirectory push origin "HEAD:$Branch" | Out-Null
            Write-Output "Published report $marketDate to $Remote/$Branch."
            if (-not $SkipDeploymentTrigger) {
                Request-PagesDeployment -RemoteUrl $remoteUrl.Trim()
            }
        }
    }
}
finally {
    if (Test-Path -LiteralPath $temporaryDirectory) {
        Remove-Item -LiteralPath $temporaryDirectory -Recurse -Force
    }
}
