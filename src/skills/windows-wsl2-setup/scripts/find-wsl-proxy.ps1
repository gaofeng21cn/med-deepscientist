param(
    [int[]]$Ports = @(7890, 1080, 10808, 10809, 20170)
)

$listeners = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalPort -in $Ports } |
    Select-Object LocalAddress, LocalPort, OwningProcess

$wslVethernet = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.InterfaceAlias -like 'vEthernet (WSL*' } |
    Select-Object -First 1 InterfaceAlias, IPAddress, PrefixLength

$processMap = @{}
foreach ($listener in $listeners) {
    if (-not $processMap.ContainsKey($listener.OwningProcess)) {
        $processName = $null
        try {
            $processName = (Get-Process -Id $listener.OwningProcess -ErrorAction Stop).ProcessName
        }
        catch {
            $processName = $null
        }
        $processMap[$listener.OwningProcess] = $processName
    }
}

$listenerDetails = @(
    foreach ($listener in $listeners) {
        [pscustomobject]@{
            LocalAddress = $listener.LocalAddress
            LocalPort = $listener.LocalPort
            OwningProcess = $listener.OwningProcess
            ProcessName = $processMap[$listener.OwningProcess]
        }
    }
)

$result = [ordered]@{
    candidate_ports = @($Ports)
    listeners = $listenerDetails
    wsl_host_ip = $wslVethernet.IPAddress
    recommendation = $null
    status = $null
}

if (-not $listenerDetails) {
    $result.status = 'no-candidate-listener'
    $result.recommendation = 'No Windows listener found on the scanned ports. Confirm whether a proxy is enabled and which port should be used.'
}
else {
    $portsFound = @($listenerDetails.LocalPort | Sort-Object -Unique)
    $nonLoopback = $listenerDetails | Where-Object { $_.LocalAddress -notin @('127.0.0.1', '::1') }

    if (-not $nonLoopback) {
        $result.status = 'loopback-only'
        $result.recommendation = 'Candidate proxy listeners are bound only to localhost. Enable LAN access before using them from WSL.'
    }
    elseif ($portsFound.Count -gt 1) {
        $result.status = 'multiple-candidates'
        $result.recommendation = 'Multiple candidate proxy ports are listening. Confirm which proxy app and port should be persisted.'
    }
    else {
        $port = $portsFound[0]
        $result.status = 'candidate-ready'
        if ($wslVethernet.IPAddress) {
            $result.recommendation = "Test WSL access with http://$($wslVethernet.IPAddress):$port"
        }
        else {
            $result.recommendation = "A non-loopback listener exists on port $port. Test that address from WSL before persisting proxy variables."
        }
    }
}

$result | ConvertTo-Json -Depth 4
