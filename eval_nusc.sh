#!/usr/bin/env bash
work_dir=$1
version=$2

#if version is mini, then use mini dataset
if [ $version == "mini" ]
then
    dataroot=vis4d/data/nuscenes/v1.0-mini #for mini
else
#else use full dataset
    dataroot=vis4d/data/nuscenes/
fi


# 3D Detection Evaluation
# python vis4d-workspace/eval_nusc.py \
# --input $work_dir/detect_3d \
# --version v1.0-${version} \
# --dataroot $dataroot \
# --mode detection

# 3D Tracking Evaluation
python eval_nusc.py \
--input $work_dir/track_3d \
--version v1.0-${version} \
--dataroot=$dataroot \
--mode tracking
