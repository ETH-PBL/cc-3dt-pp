"""Tests for pointcloud visualization."""

import glob
import shutil
import tempfile
import unittest
import warnings

import numpy as np
import torch

from tests.util import get_test_data, get_test_file
from vis4d.common.imports import OPEN3D_AVAILABLE
from vis4d.data.const import CommonKeys as K
from vis4d.data.datasets.s3dis import S3DIS
from vis4d.data.loader import DataPipe, SubdividingIterableDataset
from vis4d.data.transforms.base import compose
from vis4d.data.transforms.point_sampling import (
    GenFullCovBlockSamplingIndices,
    SampleColors,
    SampleInstances,
    SamplePoints,
    SampleSemantics,
)
from vis4d.vis.pointcloud.pointcloud_visualizer import PointCloudVisualizer

if OPEN3D_AVAILABLE:
    import open3d as o3d


class TestPointcloudViewer(unittest.TestCase):
    """Test Pointcloud viewer."""

    def setUp(self) -> None:
        """Creates a tmp directory and loads input data."""
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        """Removes the tmp directory."""
        # Remove the directory after the test
        shutil.rmtree(self.test_dir)

    def _assert_pc_equal(self, file1: str, file2: str) -> None:
        """Checks that the pointcloud stored at the given two paths are equal.

        Args:
            file1: Path to pc1
            file2:  Path to pc2
        """
        pc1 = o3d.io.read_point_cloud(file1)
        pc2 = o3d.io.read_point_cloud(file2)

        self.assertTrue(
            np.allclose(np.asarray(pc1.points), np.asarray(pc2.points))
        )
        self.assertTrue(
            np.allclose(np.asarray(pc1.colors), np.asarray(pc2.colors))
        )

    def test_precomputed(self) -> None:
        """Loads a precomputed datasamples from s3dis and checks the output."""
        if not OPEN3D_AVAILABLE:
            warnings.warn("open3d not installed, skipping test.")
            return

        test_file_loc = get_test_file("test_s3dis_pts_in.pt")
        data = torch.load(test_file_loc)
        vis = PointCloudVisualizer()
        for e in data:
            vis.process(
                points_xyz=e[K.points3d].numpy(),
                semantics=e[K.semantics3d].numpy(),
                colors=e[K.colors3d].numpy(),
                instances=e[K.instances3d].numpy(),
                scene_index=e["source_index"].numpy(),
            )

        vis.save_to_disk(self.test_dir)
        for f in glob.glob(self.test_dir + "/**/*.ply"):
            self._assert_pc_equal(
                f,
                f.replace(
                    self.test_dir, get_test_data("pointcloud_vis/s3dis")
                ),
            )

    def test_vis_s3dis(self) -> None:
        """Loads two rooms from the s3dis dataset and visualizes it."""
        if not OPEN3D_AVAILABLE:
            warnings.warn("open3d not installed, skipping test.")
            return

        s3dis = S3DIS(data_root=get_test_data("s3d_test"))
        preprocess_fn = compose(
            [
                GenFullCovBlockSamplingIndices(
                    num_pts=1024, block_dimensions=(1, 1, 4)
                ),
                SampleInstances(),
                SampleSemantics(),
                SampleColors(),
                SamplePoints(),
            ]
        )

        datapipe = DataPipe(s3dis, preprocess_fn)
        dataset = SubdividingIterableDataset(
            datapipe, n_samples_per_batch=1024
        )

        vis = PointCloudVisualizer()
        for e in dataset:
            vis.process(
                points_xyz=e[K.points3d],
                semantics=e[K.semantics3d],
                colors=e[K.colors3d],
                instances=e[K.instances3d],
                scene_index=e["source_index"],
            )

        vis.save_to_disk(self.test_dir)