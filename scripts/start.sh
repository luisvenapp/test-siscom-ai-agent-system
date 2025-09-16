#!/bin/bash  
  
# Defines the name of the virtual environment directory  
PROJDIR=$(dirname $(realpath $0))/..  
VENVNAME="${PROJDIR}/venv"  
ENV_FILE="${PROJDIR}/.env"
BACKEND_DIR="${PROJDIR}/backend"
HOST="0.0.0.0"
  
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

# Use the PORT from environment variables, or default to 8001
PORT=${PORT:-8001}
# Run the backend  
cd $BACKEND_DIR 
uvicorn main:app --host $HOST --port $PORT --reload --ws=websockets --log-level debug
