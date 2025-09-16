#!/bin/bash  
  
# Defines the name of the virtual environment directory  
PROJDIR=$(dirname $(realpath $0))/..  
VENVNAME="${PROJDIR}/venv"  
ENV_FILE="${PROJDIR}/.env"
BACKEND_DIR="${PROJDIR}/backend"
HOST="0.0.0.0"
PORT="8001"
FILE_PATH="${PROJDIR}/static/trini-info.json"

# Activate the virtual environment

# check if the virtual environment exists
if [ ! -d "$VENVNAME" ]; then  
    echo "The virtual environment $VENVNAME does not exist. Executing configure.sh..."
    # execute configure.sh
    $PROJDIR/scripts/configure.sh
fi

source $VENVNAME/bin/activate

# Load environment variables from .env file  
if [ -f "$ENV_FILE" ]; then  
    export $(cat "$ENV_FILE" | grep -v '^#' | xargs)  
fi  
  
# Run the backend  
cd $BACKEND_DIR 
python3 cli.py index --file-path  $FILE_PATH 