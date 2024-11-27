#!/bin/bash

# Path to the JSON configuration file
CONFIG_FILE="../AgentRepoConfig.json"
CLIENT_AGENT_FOLDER="../src/win-arena-container/client/mm_agents"
SERVER_AGENT_FOLDER="../src/win-arena-container/vm/setup/mm_agents"
AGENT_REPO_FOLDER="../agentRepo"

# Check if jq is installed
if ! command -v jq &> /dev/null
then
    echo "jq could not be found, installing jq..."
    sudo apt-get update && sudo apt-get install -y jq
fi

# Create the agentRepo folder if it doesn't exist
mkdir -p "$AGENT_REPO_FOLDER"

# Read the JSON file and clone the repositories
jq -c '.repositories[]' "$CONFIG_FILE" | while read repo; do
    REPO_URL=$(echo "$repo" | jq -r '.url')
    REPO_DIR_NAME=$(echo "$repo" | jq -r '.directory')
    REPO_FOLDER=$(echo "$repo" | jq -r '.folder')
    RUNNING_MODE=$(echo "$repo" | jq -r '.runningmode')

    # Set the target folder based on the running mode
    if [ "$RUNNING_MODE" == "client" ]; then
        TARGET_FOLDER="$CLIENT_AGENT_FOLDER"
    elif [ "$RUNNING_MODE" == "server" ]; then
        TARGET_FOLDER="$SERVER_AGENT_FOLDER"
    else
        echo "Invalid running mode: $RUNNING_MODE"
        exit 1
    fi

    REPO_DIR="$AGENT_REPO_FOLDER/$REPO_DIR_NAME"

    if [ -d "$REPO_DIR" ]; then
        echo "Directory $REPO_DIR already exists. Skipping clone."
    else
        echo "Cloning $REPO_URL into $REPO_DIR..."
        git clone --no-checkout "$REPO_URL" "$REPO_DIR"
        cd "$REPO_DIR"
        git sparse-checkout init --cone
        git sparse-checkout set "$REPO_FOLDER"
        git checkout
        cd -
    fi

    # Copy the specific folder to the target folder
    if [ -d "$REPO_DIR/$REPO_FOLDER" ]; then
        echo "Copying $REPO_DIR/$REPO_FOLDER to $TARGET_FOLDER..."
        mkdir -p "$TARGET_FOLDER"
        cp -r "$REPO_DIR/$REPO_FOLDER" "$TARGET_FOLDER"
    else
        echo "Folder $REPO_DIR/$REPO_FOLDER does not exist."
    fi
done
