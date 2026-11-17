$ErrorActionPreference = 'Stop'
$url = 'https://developer.download.nvidia.com/compute/cuda/12.8.1/network_installers/cuda_12.8.1_windows_network.exe'
$destination = Join-Path $env:RUNNER_TEMP 'cuda_12.8.1_windows_network.exe'
Invoke-WebRequest -Uri $url -OutFile $destination
$digest = (Get-FileHash -Algorithm SHA256 $destination).Hash.ToLowerInvariant()
if ($digest -ne '779bee8ff557255c1cf5f36e0230f081675b9bb41e44be38839920cd5209bdeb') {
    throw 'Pinned CUDA installer hash differs'
}
$process = Start-Process -FilePath $destination -ArgumentList '-s nvcc_12.8 cudart_12.8' -Wait -PassThru
if ($process.ExitCode -notin @(0,3010)) { throw "CUDA component installation failed: $($process.ExitCode)" }
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$visualStudio = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $visualStudio) { throw 'Supported Visual Studio C++ build tools are missing' }
"NEAR_VS_ROOT=$visualStudio" | Out-File -FilePath $env:GITHUB_ENV -Append -Encoding utf8
