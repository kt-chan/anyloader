<#
.SYNOPSIS
    Kills all processes that are listening on TCP port 8000.
.DESCRIPTION
    This script uses Get-NetTCPConnection to find any process with a listening socket on port 8000 (both IPv4 and IPv6),
    then terminates each process using Stop-Process -Force.
    Note: Killing system-owned processes may require running PowerShell as Administrator.
.NOTES
    Requires Windows 8/Server 2012 or newer (NetTCPIP module).
    Run with administrative privileges to kill processes owned by other users/system.
#>

param(
    [Parameter(Mandatory=$false)]
    [switch]$Force
)

# Find all TCP listening connections on port 8000
$listeningProcesses = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue

if (-not $listeningProcesses) {
    Write-Host "No processes found listening on TCP port 8000." -ForegroundColor Yellow
    return
}

Write-Host "Found $($listeningProcesses.Count) process(es) listening on port 8000:" -ForegroundColor Cyan
foreach ($conn in $listeningProcesses) {
    try {
        $proc = Get-Process -Id $conn.OwningProcess -ErrorAction Stop
        Write-Host "  - PID: $($conn.OwningProcess), Process: $($proc.ProcessName), Address: $($conn.LocalAddress)"
    }
    catch {
        Write-Host "  - PID: $($conn.OwningProcess) (process name could not be retrieved)"
    }
}

# Confirm before killing (optional)
if (-not $Force) {
    $confirmation = Read-Host "`nDo you want to kill these processes? (y/n)"
    if ($confirmation -ne 'y') {
        Write-Host "Aborted." -ForegroundColor Yellow
        return
    }
}

# Kill each process
foreach ($conn in $listeningProcesses) {
    $targetPid = $conn.OwningProcess
    try {
        Stop-Process -Id $targetPid -Force -ErrorAction Stop
        Write-Host "Killed process with PID: $targetPid" -ForegroundColor Green
    }
    catch {
        Write-Host "Failed to kill process $targetPid : $_" -ForegroundColor Red
    }
}

Write-Host "`nOperation completed." -ForegroundColor Green
