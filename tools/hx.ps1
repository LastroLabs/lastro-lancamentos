# Atalho do harness do Lastro (PowerShell). Carregue com:  . .\tools\hx.ps1
$HX = Join-Path $PSScriptRoot 'harness.py'

function hx {
    $py = if (Get-Command python -ErrorAction SilentlyContinue) { 'python' }
          elseif (Get-Command py -ErrorAction SilentlyContinue) { 'py' }
          else { $null }
    if (-not $py) {
        Write-Error "Python não encontrado. Instale o Python 3.10 ou superior em https://www.python.org/downloads/ (marque 'Add python.exe to PATH') e abra um novo terminal."
        return
    }
    & $py $HX @args
}
