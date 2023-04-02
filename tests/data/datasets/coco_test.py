"""COCO dataset testing class."""
import unittest

import torch

from tests.util import get_test_data, isclose_on_all_indices_tensor
from vis4d.data.const import CommonKeys as K
from vis4d.data.datasets.coco import COCO
from vis4d.data.transforms.to_tensor import ToTensor

IMAGE_INDICES = torch.tensor([0, 1, 40480, 80659])
IMAGE_VALUES = torch.tensor(
    [
        [173.0, 175.0, 172.0],
        [168.0, 170.0, 167.0],
        [146.0, 129.0, 121.0],
        [203.0, 192.0, 186.0],
    ]
)
INSTANCE_MASK_INDICES = torch.tensor([0, 1, 41993, 293003, 1127681])
INSTANCE_MASK_VALUES = torch.tensor([0, 0, 1, 0, 1]).byte()
SEMANTIC_MASK_INDICES = torch.tensor([0, 1, 41993, 58289, 80682])
SEMANTIC_MASK_VALUES = torch.tensor([0, 0, 16, 0, 9]).long()


class COCOTest(unittest.TestCase):
    """Test coco dataloading."""

    coco = COCO(
        data_root=get_test_data("coco_test"),
        split="train",
        keys_to_load=(
            K.images,
            K.boxes2d,
            K.boxes2d_classes,
            K.instance_masks,
        ),
    )

    def test_len(self) -> None:
        """Test if len of dataset correct."""
        self.assertEqual(len(self.coco), 2)

    def test_sample(self) -> None:
        """Test if sample loaded correctly."""
        item = self.coco[0]
        item = ToTensor().apply_to_data([item])[0]  # pylint: disable=no-member
        self.assertEqual(
            tuple(item.keys()),
            (
                "original_hw",
                "input_hw",
                "coco_image_id",
                "images",
                "boxes2d",
                "boxes2d_classes",
                "instance_masks",
            ),
        )

        self.assertEqual(item[K.input_hw], [230, 352])
        self.assertEqual(item[K.original_hw], [230, 352])
        self.assertEqual(item["coco_image_id"], 37777)

        self.assertEqual(len(item[K.boxes2d]), 14)
        self.assertEqual(len(item[K.boxes2d_classes]), 14)
        self.assertEqual(len(item[K.instance_masks]), 14)

        assert isclose_on_all_indices_tensor(
            item[K.images].permute(0, 2, 3, 1).reshape(-1, 3),
            IMAGE_INDICES,
            IMAGE_VALUES,
        )
        assert isclose_on_all_indices_tensor(
            item[K.instance_masks].reshape(-1),
            INSTANCE_MASK_INDICES,
            INSTANCE_MASK_VALUES,
        )
        assert torch.isclose(
            item[K.boxes2d][0],
            torch.tensor([102.4900, 118.4700, 110.3900, 135.7800]),
        ).all()
        assert torch.isclose(
            item[K.boxes2d_classes],
            torch.tensor(
                [58, 56, 56, 60, 72, 46, 69, 71, 49, 49, 49, 49, 56, 49]
            ).long(),
        ).all()


class COCOSegTest(unittest.TestCase):
    """Test coco dataloading."""

    coco = COCO(
        data_root=get_test_data("coco_test"),
        split="train",
        keys_to_load=(
            K.images,
            K.boxes2d,
            K.boxes2d_classes,
            K.instance_masks,
            K.segmentation_masks,
        ),
        remove_empty=True,
        minimum_box_area=10,
        use_pascal_voc_cats=True,
    )

    def test_len(self) -> None:
        """Test if len of dataset correct."""
        self.assertEqual(len(self.coco), 2)

    def test_sample(self) -> None:
        """Test if sample loaded correctly."""
        item = self.coco[0]
        item = ToTensor().apply_to_data([item])[0]  # pylint: disable=no-member
        assert tuple(item.keys()) == (
            "original_hw",
            "input_hw",
            "coco_image_id",
            "images",
            "boxes2d",
            "boxes2d_classes",
            "instance_masks",
            "segmentation_masks",
        )

        self.assertEqual(item[K.input_hw], [230, 352])
        self.assertEqual(item[K.original_hw], [230, 352])
        self.assertEqual(item["coco_image_id"], 37777)

        self.assertEqual(len(item[K.boxes2d]), 5)
        self.assertEqual(len(item[K.boxes2d_classes]), 5)
        self.assertEqual(len(item[K.instance_masks]), 5)
        self.assertEqual(item[K.segmentation_masks].shape, (1, 230, 352))

        assert isclose_on_all_indices_tensor(
            item[K.images].permute(0, 2, 3, 1).reshape(-1, 3),
            IMAGE_INDICES,
            IMAGE_VALUES,
        )
        assert isclose_on_all_indices_tensor(
            item[K.segmentation_masks].reshape(-1),
            SEMANTIC_MASK_INDICES,
            SEMANTIC_MASK_VALUES,
        )
        assert torch.isclose(
            item[K.boxes2d][0],
            torch.tensor([102.4900, 118.4700, 110.3900, 135.7800]),
        ).all()
        assert torch.isclose(
            item[K.boxes2d_classes],
            torch.tensor([16, 9, 9, 11, 9]).long(),
        ).all()