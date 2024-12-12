# Get the directory of the current script
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Path to the JSON configuration file
$CONFIG_FILE = Join-Path $SCRIPT_DIR "..\AgentRepoConfig.json"
$CLIENT_AGENT_FOLDER = Join-Path $SCRIPT_DIR "..\src\win-arena-container\client\mm_agents"
$SERVER_AGENT_FOLDER = Join-Path $SCRIPT_DIR "..\src\win-arena-container\vm\setup\mm_agents"
$AGENTS_JSON_FILE = Join-Path $SCRIPT_DIR "..\src\win-arena-container\vm\setup\agents.json"

# Debugging output to check paths
Write-Output "SCRIPT_DIR: $SCRIPT_DIR"
Write-Output "CONFIG_FILE: $CONFIG_FILE"

# Check if the configuration file exists
if (-not (Test-Path $CONFIG_FILE)) {
    Write-Output "Configuration file not found: $CONFIG_FILE"
    exit 1
}

# Remove the AGENTS_JSON_FILE if it exists
if (Test-Path $AGENTS_JSON_FILE) {
    Remove-Item $AGENTS_JSON_FILE
}

# Check if Chocolatey is installed
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Output "Chocolatey could not be found, installing Chocolatey..."
    Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
}

# Check if jq is installed
if (-not (Get-Command jq -ErrorAction SilentlyContinue)) {
    Write-Output "jq could not be found, installing jq..."
    choco install jq -y
}

# Initialize an empty array to hold server repositories
$server_repos = @()

# Read the JSON file and clone the repositories
$repos = (Get-Content $CONFIG_FILE | jq -c '.repositories[]')
foreach ($repo in $repos) {
    $REPO_URL = $repo | jq -r '.url'
    $REPO_DIR_NAME = $repo | jq -r '.name'
    $REPO_FOLDER = $repo | jq -r '.foldertocopy'
    $RUNNING_MODE = $repo | jq -r '.runningmode'

    # Set the target folder based on the running mode
    if ($RUNNING_MODE -eq "client") {
        $TARGET_FOLDER = $CLIENT_AGENT_FOLDER
    } elseif ($RUNNING_MODE -eq "server") {
        $TARGET_FOLDER = $SERVER_AGENT_FOLDER
        $server_repos += $repo
    } else {
        Write-Output "Invalid running mode: $RUNNING_MODE"
        exit 1
    }

    $REPO_DIR = Join-Path $TARGET_FOLDER $REPO_DIR_NAME

    # Clone the repository
    git clone $REPO_URL $REPO_DIR
}