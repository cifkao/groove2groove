#!/bin/bash

# script for downloading groove2groove model weights (model name should be given as argument)

if [ $# -eq 0 ]; then
    echo "No model_name provided. Valid values are: v01_drums, v01_drums_vel, v01, v0_vel"
    exit 1
fi

model_name=$1
original_dir=$(pwd)

cd "$(dirname "$0")/../../experiments"
echo "downloading ${model_name}.zip into experiments directory"
sudo wget "https://groove2groove.telecom-paris.fr/data/checkpoints/${model_name}.zip"
echo "unzipping ${model_name}.zip in ./experiments"
sudo unzip "${model_name}.zip"
echo "Done"
cd "$original_dir"