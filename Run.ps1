if (!(Test-Path -Path '.venv'))
{
	Write-Output ('Using ' + (python --version))
	Write-Output 'Creating venv at ./.venv'
	python -m venv .venv
	Write-Output 'Installing dependencies'
	pip install -r requirements.txt
}

Write-Output 'Running script'
.venv\Scripts\python.exe main.py