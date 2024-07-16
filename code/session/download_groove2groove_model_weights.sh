#!/bin/bash

original_dir=$(pwd)

cd "$(dirname "$0")/../../experiments"
echo "downloading v01_drums.zip into experiments directory"
sudo wget https://groove2groove.telecom-paris.fr/data/checkpoints/v01_drums.zip
echo "unzipping v01_drums.zip in ./experiments"
sudo unzip v01_drums.zip 

echo "downloading v01_drums_vel.zip into experiments directory"
sudo wget https://groove2groove.telecom-paris.fr/data/checkpoints/v01_drums_vel.zip
echo "unzipping v01_drums_vel.zip in ./experiments"
sudo unzip v01_drums_vel.zip 

echo "Done"
cd "$original_dir"