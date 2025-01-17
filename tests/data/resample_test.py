"""Resample index to recover the original dataset length test."""

from tests.util import get_test_data
from vis4d.data.datasets.nuscenes import NuScenes
from vis4d.data.resample import ResampleDataset


def test_resample():
    """Test RsampleDataset."""
    data_root = get_test_data("nuscenes_test", absolute_path=False)

    nusc = NuScenes(
        data_root=data_root,
        version="v1.0-mini",
        split="mini_train",
        skip_empty_samples=True,
        cache_as_binary=True,
        cached_file_path=f"{data_root}/mini_train.pkl",
    )

    dataset = ResampleDataset(dataset=nusc)

    assert len(nusc) == 323
    assert len(dataset) == 323
    # Make sure it is callable. I.e. does not crash
    _ = next(iter(dataset))
