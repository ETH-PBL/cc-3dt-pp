"""Anchor generator for 2D bounding boxes.

Modified from:
https://github.com/open-mmlab/mmdetection/blob/master/mmdet/core/anchor/anchor_generator.py
"""
from __future__ import annotations

import numpy as np
import torch
from torch import Tensor
from torch.nn.modules.utils import _pair

from .util import meshgrid


def anchor_inside_image(
    flat_anchors: Tensor, img_shape: tuple[int, int], allowed_border: int = 0
) -> Tensor:
    """Check whether the anchors are inside the border.

    Args:
        flat_anchors (Tensor): Flatten anchors, shape (n, 4).
        img_shape (tuple(int)): Shape of current image.
        allowed_border (int): The border to allow the valid anchor.
            Defaults to 0.

    Returns:
        Tensor: Flags indicating whether the anchors are inside a valid range.
    """
    img_h, img_w = img_shape
    inside_flags = (
        (flat_anchors[:, 0] >= -allowed_border)
        & (flat_anchors[:, 1] >= -allowed_border)
        & (flat_anchors[:, 2] < img_w + allowed_border)
        & (flat_anchors[:, 3] < img_h + allowed_border)
    )
    return inside_flags


class AnchorGenerator:
    """Standard anchor generator for 2D anchor-based detectors.

    Examples:
        >>> from vis4d.op.box.anchor import AnchorGenerator
        >>> self = AnchorGenerator([16], [1.], [1.], [9])
        >>> all_anchors = self.grid_priors([(2, 2)], device='cpu')
        >>> print(all_anchors)
        [tensor([[-4.5000, -4.5000,  4.5000,  4.5000],
                [11.5000, -4.5000, 20.5000,  4.5000],
                [-4.5000, 11.5000,  4.5000, 20.5000],
                [11.5000, 11.5000, 20.5000, 20.5000]])]
        >>> self = AnchorGenerator([16, 32], [1.], [1.], [9, 18])
        >>> all_anchors = self.grid_priors([(2, 2), (1, 1)], device='cpu')
        >>> print(all_anchors)
        [tensor([[-4.5000, -4.5000,  4.5000,  4.5000],
                [11.5000, -4.5000, 20.5000,  4.5000],
                [-4.5000, 11.5000,  4.5000, 20.5000],
                [11.5000, 11.5000, 20.5000, 20.5000]]), \
        tensor([[-9., -9., 9., 9.]])]
    """

    def __init__(
        self,
        strides: list[int] | list[tuple[int, int]],
        ratios: list[float],
        scales: list[int] | None = None,
        base_sizes: list[int] | None = None,
        scale_major: bool = True,
        octave_base_scale: None | int = None,
        scales_per_octave: None | int = None,
        centers: list[tuple[float, float]] | None = None,
        center_offset: float = 0.0,
    ) -> None:
        """Creates an instance of the class.

        Args:
            strides (list[int] | list[tuple[int, int]]): Strides of anchors
                in multiple feature levels in order (w, h).
            ratios (list[float]): The list of ratios between the height and
                width of anchors in a single level.
            scales (list[int] | None): Anchor scales for anchors in a single
                level. It cannot be set at the same time if `octave_base_scale`
                and `scales_per_octave` are set.
            base_sizes (list[int] | None): The basic sizes
                of anchors in multiple levels.
                If None is given, strides will be used as base_sizes.
                (If strides are non square, the shortest stride is taken.)
            scale_major (bool): Whether to multiply scales first when
                generating base anchors. If true, the anchors in the same row
                will have the same scales. By default it is True in V2.0
            octave_base_scale (int): The base scale of octave.
            scales_per_octave (int): Number of scales for each octave.
                `octave_base_scale` and `scales_per_octave` are usually used in
                retinanet and the `scales` should be None when they are set.
            centers (list[tuple[float, float]] | None): The centers of the
                anchor relative to the feature grid center in multiple feature
                levels. By default it is set to be None and not used. If a list
                of tuple of float is given, they will be used to shift the
                centers of anchors.
            center_offset (float): The offset of center in proportion to
                anchors' width and height. By default it is 0 in V2.0.
        """
        # check center and center_offset
        if center_offset != 0:
            assert centers is None, (
                "center cannot be set when center_offset"
                f"!=0, {centers} is given."
            )
        if not 0 <= center_offset <= 1:
            raise ValueError(
                "center_offset should be in range [0, 1], "
                f"{center_offset} is given."
            )
        if centers is not None:
            assert len(centers) == len(strides), (
                "The number of strides should be the same as centers, got "
                f"{strides} and {centers}"
            )

        # calculate base sizes of anchors
        self.strides = [_pair(stride) for stride in strides]
        self.base_sizes = (
            [min(stride) for stride in self.strides]
            if base_sizes is None
            else base_sizes
        )
        assert len(self.base_sizes) == len(self.strides), (
            "The number of strides should be the same as base sizes, got "
            f"{self.strides} and {self.base_sizes}"
        )

        # calculate scales of anchors
        assert (
            octave_base_scale is not None and scales_per_octave is not None
        ) ^ (scales is not None), (
            "scales and octave_base_scale with scales_per_octave cannot"
            " be set at the same time"
        )
        if scales is not None:
            self.scales = torch.Tensor(scales)
        elif octave_base_scale is not None and scales_per_octave is not None:
            octave_scales = np.array(
                [
                    2 ** (i / scales_per_octave)
                    for i in range(scales_per_octave)
                ]
            )
            scales = octave_scales * octave_base_scale  # type: ignore
            self.scales = torch.Tensor(scales)
        else:
            raise ValueError(
                "Either scales or octave_base_scale with "
                "scales_per_octave should be set"
            )

        self.octave_base_scale = octave_base_scale
        self.scales_per_octave = scales_per_octave
        self.ratios = torch.Tensor(ratios)
        self.scale_major = scale_major
        self.centers = centers
        self.center_offset = center_offset
        self.base_anchors = self.gen_base_anchors()

    @property
    def num_base_priors(self) -> list[int]:
        """list[int]: The number of priors at a point on the feature grid."""
        return [base_anchors.size(0) for base_anchors in self.base_anchors]

    @property
    def num_levels(self) -> int:
        """int: number of feature levels that the generator will be applied."""
        return len(self.strides)

    def gen_base_anchors(self) -> list[Tensor]:
        """Generate base anchors.

        Returns:
            list(torch.Tensor): Base anchors of a feature grid in multiple \
                feature levels.
        """
        multi_level_base_anchors = []
        for i, base_size in enumerate(self.base_sizes):
            center = None
            if self.centers is not None:
                center = self.centers[i]
            multi_level_base_anchors.append(
                self.gen_single_level_base_anchors(
                    base_size,
                    scales=self.scales,
                    ratios=self.ratios,
                    center=center,
                )
            )
        return multi_level_base_anchors

    def gen_single_level_base_anchors(
        self,
        base_size: int,
        scales: Tensor,
        ratios: Tensor,
        center: tuple[float, float] | None = None,
    ) -> Tensor:
        """Generate base anchors of a single level.

        Args:
            base_size (int): Basic size of an anchor.
            scales (Tensor): Scales of the anchor.
            ratios (Tensor): The ratio between between the height
                and width of anchors in a single level.
            center (tuple[float], optional): The center of the base anchor
                related to a single feature grid. Defaults to None.

        Returns:
            Tensor: Anchors in a single-level feature maps.
        """
        width, height = base_size, base_size
        if center is None:
            x_center = self.center_offset * width
            y_center = self.center_offset * height
        else:
            x_center, y_center = center

        h_ratios = torch.sqrt(ratios)
        w_ratios = 1 / h_ratios
        if self.scale_major:
            ws = (width * w_ratios[:, None] * scales[None, :]).view(-1)
            hs = (height * h_ratios[:, None] * scales[None, :]).view(-1)
        else:
            ws = (width * scales[:, None] * w_ratios[None, :]).view(-1)
            hs = (height * scales[:, None] * h_ratios[None, :]).view(-1)

        # use float anchor and the anchor's center is aligned with the
        # pixel center
        base_anchors = [
            x_center - 0.5 * ws,
            y_center - 0.5 * hs,
            x_center + 0.5 * ws,
            y_center + 0.5 * hs,
        ]

        return torch.stack(base_anchors, dim=-1)

    def grid_priors(
        self,
        featmap_sizes: list[tuple[int, int]],
        dtype: torch.dtype = torch.float32,
        device: torch.device = torch.device("cpu"),
    ) -> list[Tensor]:
        """Generate grid anchors in multiple feature levels.

        Args:
            featmap_sizes (list[tuple]): List of feature map sizes in
                multiple feature levels.
            dtype (torch.dtype): Dtype of priors. Default: torch.float32.
            device (torch.device): The device where the anchors will be put on.

        Return:
            list[Tensor]: Anchors in multiple feature levels. The sizes of each
                tensor should be [N, 4], where
                N = width * height * num_base_anchors, width and height
                are the sizes of the corresponding feature level,
                num_base_anchors is the number of anchors for that level.
        """
        assert self.num_levels == len(featmap_sizes)
        multi_level_anchors = []
        for i in range(self.num_levels):
            anchors = self.single_level_grid_priors(
                featmap_sizes[i], level_idx=i, dtype=dtype, device=device
            )
            multi_level_anchors.append(anchors)
        return multi_level_anchors

    def single_level_grid_priors(
        self,
        featmap_size: tuple[int, int],
        level_idx: int,
        dtype: torch.dtype = torch.float32,
        device: torch.device = torch.device("cpu"),
    ) -> Tensor:
        """Generate grid anchors of a single level.

        Args:
            featmap_size (tuple[int, int]): Size of the feature maps.
            level_idx (int): The index of corresponding feature map level.
            dtype (torch.dtype, optional): Data type of points. Defaults to
                torch.float32.
            device (torch.device): The device the tensor will be put on.

        Returns:
            Tensor: Anchors in the overall feature maps.
        """
        base_anchors = self.base_anchors[level_idx].to(device).to(dtype)
        feat_h, feat_w = featmap_size
        stride_w, stride_h = self.strides[level_idx]
        # First create Range with the default dtype, than convert to
        # target `dtype` for onnx exporting.
        shift_x = torch.arange(0, feat_w, device=device).to(dtype) * stride_w
        shift_y = torch.arange(0, feat_h, device=device).to(dtype) * stride_h

        shift_xx, shift_yy = meshgrid(shift_x, shift_y)
        shifts = torch.stack([shift_xx, shift_yy, shift_xx, shift_yy], dim=-1)
        # first feat_w elements correspond to the first row of shifts
        # add A anchors (1, A, 4) to K shifts (K, 1, 4) to get
        # shifted anchors (K, A, 4), reshape to (K*A, 4)

        all_anchors = base_anchors[None, :, :] + shifts[:, None, :]
        all_anchors = all_anchors.view(-1, 4)
        # first A rows correspond to A anchors of (0, 0) in feature map,
        # then (0, 1), (0, 2), ...
        return all_anchors

    def __repr__(self) -> str:
        """str: a string that describes the module."""
        indent_str = "    "
        repr_str = self.__class__.__name__ + "(\n"
        repr_str += f"{indent_str}strides={self.strides},\n"
        repr_str += f"{indent_str}ratios={self.ratios},\n"
        repr_str += f"{indent_str}scales={self.scales},\n"
        repr_str += f"{indent_str}base_sizes={self.base_sizes},\n"
        repr_str += f"{indent_str}scale_major={self.scale_major},\n"
        repr_str += f"{indent_str}octave_base_scale="
        repr_str += f"{self.octave_base_scale},\n"
        repr_str += f"{indent_str}scales_per_octave="
        repr_str += f"{self.scales_per_octave},\n"
        repr_str += f"{indent_str}num_levels={self.num_levels}\n"
        repr_str += f"{indent_str}centers={self.centers},\n"
        repr_str += f"{indent_str}center_offset={self.center_offset})"
        return repr_str