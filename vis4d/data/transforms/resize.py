"""Resize transformation."""
from __future__ import annotations

import random
from typing import TypedDict

import torch
import torch.nn.functional as F
from torch import Tensor

from vis4d.common.typing import NDArrayF32
from vis4d.data.const import CommonKeys as K
from vis4d.op.box.box2d import transform_bbox

from .base import Transform


class ResizeParam(TypedDict):
    """Parameters for Resize."""

    target_shape: tuple[int, int]
    scale_factor: tuple[float, float]
    interpolation: str


@Transform(K.images, ["transforms.resize", K.input_hw])
class GenerateResizeParameters:
    """Generate the parameters for a resize operation."""

    def __init__(
        self,
        shape: tuple[int, int] | list[tuple[int, int]],
        keep_ratio: bool = False,
        multiscale_mode: str = "range",
        scale_range: tuple[float, float] = (1.0, 1.0),
        align_long_edge: bool = False,
        allow_overflow: bool = False,
        interpolation: str = "bilinear",
    ) -> None:
        """Creates an instance of the class.

        Args:
            shape (tuple[int, int] | list[tuple[int, int]]): Image shape to
                be resized to in (H, W) format. In multiscale mode 'list',
                shape represents the list of possible shapes for resizing.
            keep_ratio (bool, optional): If aspect ratio of the original image
                should be kept, the new shape will modified to fit the aspect
                ratio of the original image. Defaults to False.
            multiscale_mode (str, optional): one of [range, list]. Defaults to
                "range".
            scale_range (tuple[float, float], optional): Range of sampled image
                scales in range mode, e.g. (0.8, 1.2), indicating minimum of
                0.8 * shape and maximum of 1.2 * shape. Defaults to (1.0, 1.0).
            align_long_edge (bool, optional): If keep_ratio=true, this option
                indicates if shape should be automatically aligned with the
                long edge of the original image, e.g. original shape=(100, 80),
                shape to be resized=(100, 200) will yield (125, 100) as new
                shape. Defaults to False.
            allow_overflow (bool, optional): If set to True, we scale the image
                to the smallest size such that it is no smaller than shape.
                Otherwise, we scale the image to the largest size such that it
                is no larger than shape. Defaults to False.
            interpolation (str, optional): Interpolation method. One of
                ["nearest", "bilinear", "bicubic"]. Defaults to "bilinear".
        """
        self.shape = shape
        self.keep_ratio = keep_ratio
        self.multiscale_mode = multiscale_mode
        self.scale_range = scale_range
        self.align_long_edge = align_long_edge
        self.allow_overflow = allow_overflow
        self.interpolation = interpolation

    def __call__(
        self, images: list[NDArrayF32]
    ) -> tuple[list[ResizeParam], list[tuple[int, int]]]:
        """Compute the parameters and put them in the data dict."""
        image = images[0]

        im_shape = (image.shape[1], image.shape[2])
        target_shape = get_target_shape(
            im_shape,
            self.shape,
            self.keep_ratio,
            self.multiscale_mode,
            self.scale_range,
            self.align_long_edge,
            self.allow_overflow,
        )
        scale_factor = (
            target_shape[1] / im_shape[1],
            target_shape[0] / im_shape[0],
        )

        resize_params = [
            ResizeParam(
                target_shape=target_shape,
                scale_factor=scale_factor,
                interpolation=self.interpolation,
            )
        ] * len(images)
        target_shapes = [target_shape] * len(images)

        return resize_params, target_shapes


@Transform(
    [
        K.images,
        "transforms.resize.target_shape",
        "transforms.resize.interpolation",
    ],
    K.images,
)
class ResizeImages:
    """Resize Images."""

    def __call__(
        self,
        images: list[NDArrayF32],
        target_shapes: list[tuple[int, int]],
        interpolations: list[str],
        antialias: bool = False,
    ) -> list[NDArrayF32]:
        """Resize an image of dimensions [N, H, W, C].

        Args:
            image (Tensor): The image.
            target_shape (tuple[int, int]): The target shape after resizing.
            interpolation (str): One of nearest, bilinear, bicubic. Defaults to
                bilinear.
            antialias (bool): Whether to use antialiasing. Defaults to False.

        Returns:
            list[NDArrayF32]: Resized images according to parameters in resize.
        """
        for i, (image, target_shape, interpolation) in enumerate(
            zip(images, target_shapes, interpolations)
        ):
            image_ = torch.from_numpy(image).permute(0, 3, 1, 2)
            image_ = resize_tensor(
                image_,
                target_shape,
                interpolation=interpolation,
                antialias=antialias,
            )
            images[i] = image_.permute(0, 2, 3, 1).numpy()
        return images


@Transform([K.boxes2d, "transforms.resize.scale_factor"], K.boxes2d)
class ResizeBoxes2D:
    """Resize list of 2D bounding boxes."""

    def __call__(
        self,
        boxes_list: list[NDArrayF32],
        scale_factors: list[tuple[float, float]],
    ) -> list[NDArrayF32]:
        """Resize 2D bounding boxes.

        Args:
            boxes_list: (list[NDArrayF32]): The bounding boxes to be resized.
            scale_factors (list[tuple[float, float]]): scaling factors.

        Returns:
            list[NDArrayF32]: Resized bounding boxes according to parameters in
                resize.
        """
        for i, (boxes, scale_factor) in enumerate(
            zip(boxes_list, scale_factors)
        ):
            boxes_ = torch.from_numpy(boxes)
            scale_matrix = torch.eye(3)
            scale_matrix[0, 0] = scale_factor[0]
            scale_matrix[1, 1] = scale_factor[1]
            boxes_list[i] = transform_bbox(scale_matrix, boxes_).numpy()
        return boxes_list


@Transform(
    [K.instance_masks, "transforms.resize.target_shape"], K.instance_masks
)
class ResizeInstanceMasks:
    """Resize instance segmentation masks."""

    def __call__(
        self,
        masks_list: list[NDArrayF32],
        target_shapes: list[tuple[int, int]],
    ) -> list[NDArrayF32]:
        """Resize masks."""
        for i, (masks, target_shape) in enumerate(
            zip(masks_list, target_shapes)
        ):
            if len(masks) == 0:  # handle empty masks
                continue
            masks_ = torch.from_numpy(masks)
            masks_ = (
                resize_tensor(
                    masks_.float().unsqueeze(1),
                    target_shape,
                    interpolation="nearest",
                )
                .type(masks_.dtype)
                .squeeze(1)
            )
            masks_list[i] = masks_.numpy()
        return masks_list


@Transform([K.seg_masks, "transforms.resize.target_shape"], K.seg_masks)
class ResizeSegMasks:
    """Resize segmentation masks."""

    def __call__(
        self,
        masks_list: list[NDArrayF32],
        target_shape_list: list[tuple[int, int]],
    ) -> list[NDArrayF32]:
        """Resize masks."""
        for i, (masks, target_shape) in enumerate(
            zip(masks_list, target_shape_list)
        ):
            masks_ = torch.from_numpy(masks)
            masks_ = (
                resize_tensor(
                    masks_.float().unsqueeze(0).unsqueeze(0),
                    target_shape,
                    interpolation="nearest",
                )
                .type(masks_.dtype)
                .squeeze(0)
                .squeeze(0)
            )
            masks_list[i] = masks_.numpy()
        return masks_list


@Transform([K.intrinsics, "transforms.resize.scale_factor"], K.intrinsics)
class ResizeIntrinsics:
    """Resize Intrinsics."""

    def __call__(
        self,
        intrinsics: list[NDArrayF32],
        scale_factors: list[tuple[float, float]],
    ) -> list[NDArrayF32]:
        """Scale camera intrinsics when resizing."""
        for i, scale_factor in enumerate(scale_factors):
            intrinsics[i][0, 0] *= scale_factor[0]
            intrinsics[i][1, 1] *= scale_factor[1]
        return intrinsics


def resize_tensor(
    inputs: Tensor,
    shape: tuple[int, int],
    interpolation: str = "bilinear",
    antialias: bool = False,
) -> Tensor:
    """Resize Tensor."""
    assert interpolation in {"nearest", "bilinear", "bicubic"}
    align_corners = None if interpolation == "nearest" else False
    output = F.interpolate(
        inputs,
        shape,
        mode=interpolation,
        align_corners=align_corners,
        antialias=antialias,
    )
    return output


def get_resize_shape(
    original_shape: tuple[int, int],
    new_shape: tuple[int, int],
    keep_ratio: bool = True,
    align_long_edge: bool = False,
    allow_overflow: bool = False,
) -> tuple[int, int]:
    """Get shape for resize, considering keep_ratio and align_long_edge."""
    h, w = original_shape
    new_h, new_w = new_shape
    if keep_ratio:
        if allow_overflow:
            comp_fn = max
        else:
            comp_fn = min
        if align_long_edge:
            long_edge, short_edge = max(new_shape), min(new_shape)
            scale_factor = comp_fn(
                long_edge / max(h, w), short_edge / min(h, w)
            )
        else:
            scale_factor = comp_fn(new_w / w, new_h / h)
        new_h = int(h * scale_factor + 0.5)
        new_w = int(w * scale_factor + 0.5)
    return new_h, new_w


def get_target_shape(
    input_shape: tuple[int, int],
    shape: tuple[int, int] | list[tuple[int, int]],
    keep_ratio: bool = False,
    multiscale_mode: str = "range",
    scale_range: tuple[float, float] = (1.0, 1.0),
    align_long_edge: bool = False,
    allow_overflow: bool = False,
) -> tuple[int, int]:
    """Generate possibly random target shape."""
    assert multiscale_mode in {"list", "range"}
    if multiscale_mode == "list":
        assert isinstance(
            shape, list
        ), "Specify shape as list when using multiscale mode list."
        assert len(shape) >= 1
    else:
        assert isinstance(
            shape, tuple
        ), "Specify shape as tuple when using multiscale mode range."
        assert (
            scale_range[0] <= scale_range[1]
        ), f"Invalid scale range: {scale_range[1]} < {scale_range[0]}"

    if multiscale_mode == "range":
        assert isinstance(shape, tuple)
        if scale_range[0] < scale_range[1]:  # do multi-scale
            w_scale = (
                random.uniform(0, 1) * (scale_range[1] - scale_range[0])
                + scale_range[0]
            )
            h_scale = (
                random.uniform(0, 1) * (scale_range[1] - scale_range[0])
                + scale_range[0]
            )
        else:
            h_scale = w_scale = 1.0

        shape = int(shape[0] * h_scale), int(shape[1] * w_scale)
    else:
        assert isinstance(shape, list)
        shape = random.choice(shape)

    shape = get_resize_shape(
        input_shape, shape, keep_ratio, align_long_edge, allow_overflow
    )
    return shape
