#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status.

# Check if conda command is available
if ! type conda > /dev/null; then
  echo "Conda is not available. Please ensure Conda is installed and initialized."
  exit 1
fi

# Set default radar config file path
DEFAULT_CONFIG="/root/cc3dt/vis4d/data/nuscenes/radar_detect_sweep_num2_fullnusc.json"

# Check for the minimum number of arguments
if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <dataset-type> [radar-config-file]"
  exit 1
fi

# Set dataset type from the first argument
DATASET_TYPE=$1

# Set radar config file path; use default if not provided
RADAR_CONFIG="${2:-$DEFAULT_CONFIG}"

# Choose the appropriate configuration file based on the dataset type
if [ "$DATASET_TYPE" = "mini" ]; then
  CONFIG_FILE="vis4d/zoo/cc_3dt/cr3dt_kf3d_nusc_mini.py"
  WORK_DIR="vis4d/vis4d-workspace/cr3dt_kf3d_nusc_mini"
else
  CONFIG_FILE="vis4d/zoo/cc_3dt/cr3dt_kf3d_nusc.py"
  WORK_DIR="vis4d/vis4d-workspace/cr3dt_kf3d_nusc"
fi

# Navigate to the vis4d directory
cd vis4d || exit

# Activate the cc3dt Conda environment
source activate cc3dt

# Execute the vis4d-pl test command and extract the output directory
vis4d-pl test --config "$CONFIG_FILE" --gpus 1 --ckpt /root/cc3dt/vis4d/data/nuscenes/cc_3dt_frcnn_r101_fpn_24e_nusc_f24f84.pt --config.pure_detection "$RADAR_CONFIG"

# Get the newest directory
cd .. || exit
cd "$WORK_DIR" || exit
NEWEST_DIR=$(ls -td -- */ | head -n 1 | cut -d'/' -f1)

# Check if the NEWEST_DIR variable is set, if not exit the script
if [ -z "$NEWEST_DIR" ]; then
  echo "Newest directory could not be determined."
  exit 1
fi

# Construct the full path to the newest directory
FULL_PATH="$WORK_DIR/$NEWEST_DIR"

# Navigate back to the initial directory
cd /root/cc3dt || exit

conda deactivate
# Activate the cc3dt_vis4d Conda environment for evaluation
source activate cc3dt_track

echo $FULL_PATH

# Execute the eval_nusc.sh script with the dynamically determined timestamp and dataset type
bash eval_nusc.sh "${FULL_PATH}/" "$DATASET_TYPE"
