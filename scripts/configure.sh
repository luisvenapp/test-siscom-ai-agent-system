#!/bin/bash  

# Defines the name of the virtual environment directory
# .
# scripts
#   |- configure.sh
# backend
#   |- requirements.txt
# venv

# get the parent where this script is located (the project root)

PROJDIR=$(dirname $(realpath $0))/.. 
VENVNAME="${PROJDIR}/venv"
REQUIREMENT_FILE="${PROJDIR}/requirements.txt"

# check if the virtual environment exists
if [ ! -d "$VENVNAME" ]; then  
    echo "The virtual environment $VENVNAME does not exist. Creating..."
    # install venv using apt
    sudo apt-get install python3-venv -y
    pip3 install virtualenv
    python3 -m venv $VENVNAME

fi  
  
# Activate the virtual environment
source $VENVNAME/bin/activate  

# Install dependencies

if [ -f "$REQUIREMENT_FILE" ]; then  
    echo "Installing dependencies..." 
    # Instalar las dependencias  
    pip install -r $REQUIREMENT_FILE  
else  
    echo "Could not find a requirements.txt file."
fi  
