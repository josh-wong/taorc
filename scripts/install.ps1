#!/usr/bin/env pwsh
<#
.SYNOPSIS
    taorc installer -- see v1-design-doc.md §6.3 and §9 item 8.

.DESCRIPTION
    Places the taorc managed block (templates/agent-block.md, wrapped in
    <!-- taorc:begin/end --> markers) into every instructions file an
    installed harness reads, plus a copy of the skill directory for
    harnesses that read SKILL.md directly. Never touches anything outside
    the markers in a file that already exists, so it is safe to run against
    a project's own AGENTS.md / CLAUDE.md. Mirrors install.sh's behavior and
    flag surface; see that script's header for the shared design notes.

.PARAMETER Scope
    'Project' (default) or 'Global'.

.PARAMETER Dir
    Target directory for -Scope Project. Default: the current directory.

.PARAMETER Source
    A local taorc checkout to install from, instead of downloading one.
    Mainly for testing and offline use.

.PARAMETER Agents
    Comma-separated subset of: claude, copilot, cursor, cline, windsurf,
    gemini, agents. Default: all.

.PARAMETER Detect
    Only refresh adapters that are already installed; never create a new one.

.PARAMETER Uninstall
    Remove the taorc managed block from every adapter and delete the skill
    directory copies. Leaves any content outside the markers untouched.

.NOTES
    Set the TAORC_REF environment variable to a branch, tag, or commit SHA,
    such as v1.0.0, to download that ref instead of main when -Source is not
    given. Fetch this script from the same ref you pin, or a newer installer
    runs against older files.
#>

[CmdletBinding()]
param(
    [ValidateSet("Project", "Global")]
    [string]$Scope = "Project",

    [string]$Dir,

    [string]$Source,

    [string]$Agents = "claude,copilot,cursor,cline,windsurf,gemini,agents",

    [switch]$Detect,

    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

$RepoSlug = "josh-wong/taorc"
$AllAgents = @("claude", "copilot", "cursor", "cline", "windsurf", "gemini", "agents")

function Write-Log([string]$Message) {
    Write-Host "taorc-install: $Message"
}

function Fail([string]$Message) {
    Write-Error "taorc-install: error: $Message"
    exit 1
}

# ---- resolve scope and agent list --------------------------------------

$agentList = ($Agents -split ",") | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }
foreach ($agent in $agentList) {
    if ($AllAgents -notcontains $agent) {
        Fail "unknown -Agents value '$agent' (choose from: $($AllAgents -join ', '))"
    }
}

if ($Scope -eq "Global") {
    if ($Dir) { Fail "-Dir cannot be combined with -Scope Global" }
    $TargetDir = $HOME
}
else {
    $TargetDir = if ($Dir) { $Dir } else { (Get-Location).Path }
}

if (-not (Test-Path -LiteralPath $TargetDir -PathType Container)) {
    Fail "target directory does not exist: $TargetDir"
}

# ---- resolve the taorc source tree --------------------------------------

$downloadDir = $null
$workDir = New-Item -ItemType Directory -Path (Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid()))

try {
    if (-not $Source) {
        # -CommandType Application so an alias or function named tar can't
        # stand in for it: only a real program sets $LASTEXITCODE.
        if (-not (Get-Command tar -CommandType Application -ErrorAction SilentlyContinue)) {
            Fail "tar is required to unpack taorc (or pass -Source for an offline install)"
        }
        $ref = if ($env:TAORC_REF) { $env:TAORC_REF } else { "main" }
        $downloadDir = New-Item -ItemType Directory -Path (Join-Path ([System.IO.Path]::GetTempPath()) ([System.Guid]::NewGuid()))
        # The ref-agnostic archive path, not refs/heads/, so a release tag or a
        # commit SHA resolves as well as a branch.
        $archiveUrl = "https://github.com/$RepoSlug/archive/$ref.tar.gz"
        $archivePath = Join-Path $downloadDir.FullName "taorc.tar.gz"
        Write-Log "downloading $archiveUrl"
        try {
            Invoke-WebRequest -Uri $archiveUrl -OutFile $archivePath -UseBasicParsing
        }
        catch {
            Fail "failed to download $archiveUrl (check that TAORC_REF names an existing branch, tag, or commit; release tags start with v. Or pass -Source for an offline install.)"
        }
        # tar's nonzero exit doesn't stop the script, so without the check
        # below a failed extraction would surface one step later as a missing
        # directory, hiding the real cause. "Continue" for this one command
        # keeps that check reachable: under "Stop", Windows PowerShell 5.1
        # makes each line tar writes to a redirected stderr fatal, and newer
        # versions do the same with a nonzero exit when the session has
        # $PSNativeCommandUseErrorActionPreference turned on.
        & {
            $ErrorActionPreference = "Continue"
            tar -xzf $archivePath -C $downloadDir.FullName
        }
        if ($LASTEXITCODE -ne 0) {
            Fail "tar exited $LASTEXITCODE while extracting the archive downloaded from $archiveUrl; see tar's error above (pass -Source for an offline install)"
        }
        # Reachable even when tar succeeds: bsdtar, the tar.exe Windows ships,
        # exits 0 on an empty download.
        $extracted = Get-ChildItem -Path $downloadDir.FullName -Directory -Filter "taorc-*" | Select-Object -First 1
        if (-not $extracted) {
            Fail "no taorc source found in the archive downloaded from $archiveUrl (the download may be empty or not a taorc archive; pass -Source for an offline install)"
        }
        $Source = $extracted.FullName
    }

    if (-not (Test-Path (Join-Path $Source "VERSION"))) {
        Fail "$Source does not look like a taorc checkout (no VERSION file)"
    }
    if (-not (Test-Path (Join-Path $Source "skills/readable-code"))) {
        Fail "$Source is missing skills/readable-code"
    }

    $version = (Get-Content (Join-Path $Source "VERSION") -Raw).Trim()
    $beginPrefix = "<!-- taorc:begin"
    $endMarker = "<!-- taorc:end -->"

    # ---- render the managed block ---------------------------------------

    $templateLines = Get-Content (Join-Path $Source "templates/agent-block.md")
    $first = 0
    while ($first -lt $templateLines.Count -and $templateLines[$first].Trim() -eq "") { $first++ }
    $last = $templateLines.Count - 1
    while ($last -ge $first -and $templateLines[$last].Trim() -eq "") { $last-- }
    $trimmedTemplate = if ($first -le $last) { $templateLines[$first..$last] } else { @() }

    $blockLines = @("$beginPrefix v$version -->") + $trimmedTemplate + @($endMarker)
    $blockText = ($blockLines -join "`n") + "`n"

    # A trailing "`n" is appended explicitly: PowerShell here-strings drop the
    # final blank line before the closing "@, so without it these would be
    # missing the blank-line separator install.sh's equivalent heredocs keep.
    $cursorFrontmatter = (@"
---
description: Write, comment, and review code so the next reader understands it in the least time.
alwaysApply: true
---
"@) + "`n`n"

    $copilotInstructionsFrontmatter = (@"
---
applyTo: "**/*"
---
"@) + "`n`n"

    # ---- per-agent target lists -----------------------------------------

    function Get-AgentTargets([string]$agent) {
        switch ($agent) {
            "claude" {
                , @{ Kind = "block"; RelPath = "AGENTS.md"; Frontmatter = $null }
                , @{ Kind = "block"; RelPath = "CLAUDE.md"; Frontmatter = $null }
                , @{ Kind = "skill"; RelPath = ".claude/skills/readable-code"; Frontmatter = $null }
            }
            "copilot" {
                , @{ Kind = "block"; RelPath = ".github/copilot-instructions.md"; Frontmatter = $null }
                , @{ Kind = "block"; RelPath = ".github/instructions/readable-code.instructions.md"; Frontmatter = $copilotInstructionsFrontmatter }
                , @{ Kind = "skill"; RelPath = ".github/skills/readable-code"; Frontmatter = $null }
            }
            "cursor" {
                , @{ Kind = "block"; RelPath = ".cursor/rules/readable-code.mdc"; Frontmatter = $cursorFrontmatter }
            }
            "cline" {
                , @{ Kind = "block"; RelPath = ".clinerules/readable-code.md"; Frontmatter = $null }
            }
            "windsurf" {
                , @{ Kind = "block"; RelPath = ".windsurf/rules/readable-code.md"; Frontmatter = $null }
                , @{ Kind = "block"; RelPath = "AGENTS.md"; Frontmatter = $null }
            }
            "gemini" {
                , @{ Kind = "block"; RelPath = "GEMINI.md"; Frontmatter = $null }
            }
            "agents" {
                , @{ Kind = "block"; RelPath = "AGENTS.md"; Frontmatter = $null }
            }
            default { Fail "unknown agent: $agent" }
        }
    }

    $targets = @{}
    foreach ($agent in $agentList) {
        foreach ($target in (Get-AgentTargets $agent)) {
            $key = "$($target.Kind):$($target.RelPath)"
            $targets[$key] = $target
        }
    }

    # ---- apply / remove one managed block --------------------------------

    function Apply-Block([string]$targetPath, [string]$frontmatter) {
        if ($Detect -and -not (Test-Path $targetPath)) {
            Write-Log "skip (not installed): $targetPath"
            return
        }

        $parent = Split-Path $targetPath -Parent
        if ($parent -and -not (Test-Path $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }

        if (-not (Test-Path $targetPath)) {
            $content = if ($frontmatter) { $frontmatter + $blockText } else { $blockText }
            [System.IO.File]::WriteAllText($targetPath, $content)
            Write-Log "created $targetPath"
            return
        }

        $existingLines = Get-Content -LiteralPath $targetPath
        $hasBegin = $existingLines | Where-Object { $_.Contains($beginPrefix) } | Select-Object -First 1
        $hasEnd = $existingLines | Where-Object { $_.Contains($endMarker) } | Select-Object -First 1

        if (($hasBegin -and -not $hasEnd) -or ($hasEnd -and -not $hasBegin)) {
            Fail "$targetPath`: has a taorc managed-block begin marker without a matching end marker (or vice versa) -- fix the file by hand before running install.ps1"
        }

        if ($hasBegin -and $hasEnd) {
            # Line-based, like install.sh's awk equivalent: a line containing a
            # marker is dropped in its entirety, not sliced at the marker text,
            # and a missing end marker (inBlock never clears) drops everything
            # from the begin line to EOF instead of computing a bogus offset.
            $outputLines = New-Object System.Collections.Generic.List[string]
            $inBlock = $false
            foreach ($line in $existingLines) {
                if (-not $inBlock -and $line.Contains($beginPrefix)) {
                    $outputLines.Add($blockText.TrimEnd("`n"))
                    $inBlock = $true
                    continue
                }
                if ($inBlock -and $line.Contains($endMarker)) {
                    $inBlock = $false
                    continue
                }
                if ($inBlock) { continue }
                $outputLines.Add($line)
            }
            $updated = ($outputLines -join "`n") + "`n"
            [System.IO.File]::WriteAllText($targetPath, $updated)
            Write-Log "updated $targetPath"
        }
        else {
            $existingRaw = Get-Content -LiteralPath $targetPath -Raw
            if (-not $existingRaw) { $existingRaw = "" }
            $separator = if ($existingRaw -and -not $existingRaw.EndsWith("`n")) { "`n" } else { "" }
            [System.IO.File]::WriteAllText($targetPath, $existingRaw + $separator + $blockText)
            Write-Log "appended to $targetPath"
        }
    }

    function Remove-Block([string]$targetPath) {
        if (-not (Test-Path $targetPath)) { return }
        $existingLines = Get-Content -LiteralPath $targetPath
        if (-not $existingLines) { return }
        $hasBegin = $existingLines | Where-Object { $_.Contains($beginPrefix) } | Select-Object -First 1
        $hasEnd = $existingLines | Where-Object { $_.Contains($endMarker) } | Select-Object -First 1
        if (-not $hasBegin -and -not $hasEnd) { return }
        if (($hasBegin -and -not $hasEnd) -or ($hasEnd -and -not $hasBegin)) {
            Fail "$targetPath`: has a taorc managed-block begin marker without a matching end marker (or vice versa) -- fix the file by hand before running -Uninstall"
        }

        $outputLines = New-Object System.Collections.Generic.List[string]
        $inBlock = $false
        foreach ($line in $existingLines) {
            if (-not $inBlock -and $line.Contains($beginPrefix)) {
                $inBlock = $true
                continue
            }
            if ($inBlock -and $line.Contains($endMarker)) {
                $inBlock = $false
                continue
            }
            if ($inBlock) { continue }
            $outputLines.Add($line)
        }

        $remaining = if ($outputLines.Count -gt 0) { ($outputLines -join "`n") + "`n" } else { "" }

        # Mirrors install.sh's `tr -d '[:space:]-'` emptiness check, which also
        # strips hyphens (e.g. a lone leftover "---" frontmatter fence), so both
        # installers delete the same files on uninstall.
        if (-not $remaining -or ($remaining -replace '[\s-]', '') -eq "") {
            Remove-Item $targetPath -Force
            Write-Log "removed (now empty) $targetPath"
        }
        else {
            [System.IO.File]::WriteAllText($targetPath, $remaining)
            Write-Log "removed taorc block from $targetPath"
        }
    }

    function Apply-SkillCopy([string]$destPath) {
        if ($Uninstall) {
            if (Test-Path $destPath) {
                Remove-Item $destPath -Recurse -Force
                Write-Log "removed $destPath"
            }
            return
        }
        if ($Detect -and -not (Test-Path $destPath)) {
            Write-Log "skip (not installed): $destPath"
            return
        }
        $parent = Split-Path $destPath -Parent
        if ($parent -and -not (Test-Path $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }

        # Guard against -Source and the install target overlapping (e.g.
        # running against a taorc checkout's own directory by mistake):
        # refuse to remove a destPath that is the source tree or sits
        # inside it, rather than deleting part of what we're about to copy
        # from. Mirrors install.sh's equivalent check.
        if (Test-Path $destPath) {
            $destAbs = (Resolve-Path -LiteralPath $destPath).Path
            $sourceAbs = (Resolve-Path -LiteralPath $Source).Path
            if ($destAbs -eq $sourceAbs -or $destAbs.StartsWith($sourceAbs + [System.IO.Path]::DirectorySeparatorChar)) {
                Fail "refusing to remove $destPath`: it is inside -Source ($Source)"
            }
            Remove-Item $destPath -Recurse -Force
        }
        Copy-Item (Join-Path $Source "skills/readable-code") $destPath -Recurse -Force
        Get-ChildItem -Path $destPath -Recurse -Force -Directory -Filter "__pycache__" |
            ForEach-Object { Remove-Item $_.FullName -Recurse -Force }
        Get-ChildItem -Path $destPath -Recurse -Force -Filter ".DS_Store" -File |
            ForEach-Object { Remove-Item $_.FullName -Force }
        Write-Log "installed $destPath"
    }

    # ---- run --------------------------------------------------------------

    foreach ($key in ($targets.Keys | Sort-Object)) {
        $target = $targets[$key]
        $targetPath = Join-Path $TargetDir $target.RelPath
        switch ($target.Kind) {
            "block" {
                if ($Uninstall) { Remove-Block $targetPath }
                else { Apply-Block $targetPath $target.Frontmatter }
            }
            "skill" {
                Apply-SkillCopy $targetPath
            }
        }
    }

    if ($Uninstall) {
        Write-Log "uninstall complete."
    }
    else {
        Write-Log "install complete (v$version, scope: $Scope, target: $TargetDir)."
    }
}
finally {
    if ($downloadDir) { Remove-Item $downloadDir.FullName -Recurse -Force -ErrorAction SilentlyContinue }
    Remove-Item $workDir.FullName -Recurse -Force -ErrorAction SilentlyContinue
}
