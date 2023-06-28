#!/bin/bash
#SBATCH --job-name=Vis4D                    # Job name
#SBATCH --nodes=1                           # Numbers of node
#SBATCH --ntasks=8                          # Numbers of task
#SBATCH --ntasks-per-node=8                 # Tasks per node
#SBATCH --cpus-per-task=4                   # Cores of cpu per task
#SBATCH --mem-per-cpu=4G                    # Memory per core
#SBATCH --gpus-per-node=8                   # Numbers of gpu per node
#SBATCH --gres=gpumem:20G                   # Memory per gpu
#SBATCH --time=24:00:00                     # 4h / 24h / 120h
#SBATCH --tmp=100G                          # Local scratch

module load gcc/8.2.0
module load zlib/1.2.9
module load python/3.10.4
module load cuda/11.7.0

export PYTHONPATH=
source /cluster/home/$USER/vis4d/bin/activate

srun --cpus-per-task=4 --gres=gpumem:20G --kill-on-bad-exit=1 \
    python -m vis4d.engine.run fit \
    --config configs/faster_rcnn/faster_rcnn_coco.py \
    --gpus 8 \
    --slurm True
