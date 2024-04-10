"""Pointwise transformations."""

from __future__ import annotations

from typing import TypedDict

import numpy as np

from vis4d.common.typing import NDArrayFloat
from vis4d.data.const import CommonKeys as K

from .base import Transform


@Transform(in_keys=K.points3d, out_keys="transforms.pc_bounds")
class GenPcBounds:
    """Extracts the max and min values of the loaded points."""

    def __call__(
        self, coordinates_list: list[NDArrayFloat]
    ) -> list[NDArrayFloat]:
        """Extracts the max and min values of the pointcloud."""
        coordinates = coordinates_list[0]

        pc_bounds = [np.stack([coordinates.min(0), coordinates.max(0)])] * len(
            coordinates_list
        )

        return pc_bounds


@Transform(in_keys=(K.points3d, "trasforms.pc_bounds"), out_keys=K.points3d)
class NormalizeByMaxBounds:
    """Normalizes the pointcloud by the max bounds."""

    def __init__(self, axes: tuple[int, int, int] = (0, 1, 2)) -> None:
        """Creates an instance of the class.

        Args:
            axes (tuple[int, int, int]): Over which axes to apply
                normalization.
        """
        self.axes = axes

    def __call__(
        self,
        coords_list: list[NDArrayFloat],
        pc_bounds_list: list[NDArrayFloat],
    ) -> list[NDArrayFloat]:
        """Applies the normalization."""
        for i, (coords, pc_bounds) in enumerate(
            zip(coords_list, pc_bounds_list)
        ):
            max_bound = np.max(np.abs(pc_bounds), axis=0)
            for ax in self.axes:
                coords[:, ax] = coords[:, ax] / max_bound[ax]
            coords_list[i] = coords
        return coords_list


@Transform(in_keys=K.points3d, out_keys=K.points3d)
class CenterAndNormalize:
    """Centers and normalizes the pointcloud."""

    def __init__(self, centering: bool = True, normalize: bool = True) -> None:
        """Creates an instance of the class.

        Args:
            centering (bool): Whether to center the pointcloud
            normalize (bool): Whether to normalize the pointcloud
        """
        self.centering = centering
        self.normalize = normalize

    def __call__(self, coords_list: list[NDArrayFloat]) -> list[NDArrayFloat]:
        """Applies the Center and Normalization operations."""
        for i, coords in enumerate(coords_list):
            if self.centering:
                coords = coords - np.mean(coords, axis=0)
            if self.normalize:
                coords = coords / np.max(np.sqrt(np.sum(coords**2, axis=-1)))
            coords_list[i] = coords
        return coords_list


@Transform(in_keys=K.points3d, out_keys=K.points3d)
class AddGaussianNoise:
    """Adds random normal distributed noise with given std to the data.

    Args:
        std (float): Standard Deviation of the noise
    """

    def __init__(self, noise_level: float = 0.01):
        """Creates an instance of the class.

        Args:
            noise_level (float): The noise level. Standard deviation for
                the gaussian noise.
        """
        self.noise_level = noise_level

    def __call__(
        self, coordinates_list: list[NDArrayFloat]
    ) -> list[NDArrayFloat]:
        """Adds gaussian noise to the coordiantes."""
        for i, coordinates in enumerate(coordinates_list):
            coordinates[i] = (
                coordinates
                + np.random.randn(*coordinates.shape) * self.noise_level
            )
        return coordinates_list


@Transform(in_keys=K.points3d, out_keys=K.points3d)
class AddUniformNoise:
    """Adds random normal distributed noise with given std to the data.

    Args:
        std (float): Standard Deviation of the noise
    """

    def __init__(self, noise_level: float = 0.01):
        """Creates an instance of the class.

        Args:
            noise_level (float): The noise level. Half the range of the
                uniform noise. The noise is sampled from
                [-noise_level, noise_level].
        """
        self.noise_level = noise_level

    def __call__(
        self, coordinates_list: list[NDArrayFloat]
    ) -> list[NDArrayFloat]:
        """Adds uniform noise to the coordinates."""
        for i, coordinates in enumerate(coordinates_list):
            coordinates_list[i] = coordinates + np.random.uniform(
                -self.noise_level, self.noise_level, coordinates.shape
            )
        return coordinates_list


class SE3Transform(TypedDict):
    """Parameters for Resize."""

    translation: NDArrayFloat
    rotation: NDArrayFloat


def _gen_random_se3_transform(
    translation_min: NDArrayFloat,
    translation_max: NDArrayFloat,
    rotation_min: NDArrayFloat,
    rotation_max: NDArrayFloat,
) -> SE3Transform:
    """Creates a random SE3 Transforms.

    The transform is generated by sampling a random translation and
    rotation from a uniform distribution.
    """
    angle = np.random.uniform(rotation_min, rotation_max)
    translation = np.random.uniform(translation_min, translation_max)
    cos_x, sin_x = np.cos(angle[0]), np.sin(angle[0])
    cos_y, sin_y = np.cos(angle[1]), np.sin(angle[1])
    cos_z, sin_z = np.cos(angle[2]), np.sin(angle[2])
    rotx = np.array([[1, 0, 0], [0, cos_x, -sin_x], [0, sin_x, cos_x]])
    roty = np.array([[cos_y, 0, sin_y], [0, 1, 0], [-sin_y, 0, cos_y]])
    rotz = np.array([[cos_z, -sin_z, 0], [sin_z, cos_z, 0], [0, 0, 1]])
    rot = np.dot(rotz, np.dot(roty, rotx))
    return SE3Transform(translation=translation, rotation=rot)


@Transform(in_keys=K.points3d, out_keys=K.points3d)
class ApplySE3Transform:
    """Applies a given SE3 Transform to the data."""

    def __init__(
        self,
        translation_min: tuple[float, float, float] = (0.0, 0.0, 0.0),
        translation_max: tuple[float, float, float] = (0.0, 0.0, 0.0),
        rotation_min: tuple[float, float, float] = (0.0, 0.0, 0.0),
        rotation_max: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> None:
        """Creates an instance of the class.

        Args:
            translation_min (tuple[float, float, float]): Minimum translation.
            translation_max (tuple[float, float, float]): Maximum translation.
            rotation_min (tuple[float, float, float]):  Minimum euler rotation
                angles [rad]. Applied in the order rot_x -> rot_y -> rot_z.
            rotation_max (tuple[float, float, float]): Maximum euler rotation
                angles [rad]. Applied in the order rot_x -> rot_y -> rot_z.
        """
        self.translation_min = np.asarray(translation_min)
        self.translation_max = np.asarray(translation_max)
        self.rotation_min = np.asarray(rotation_min)
        self.rotation_max = np.asarray(rotation_max)

    def __call__(
        self, coordinates_list: list[NDArrayFloat]
    ) -> list[NDArrayFloat]:
        """Applies a SE3 Transform."""
        for i, coordinates in enumerate(coordinates_list):
            transform = _gen_random_se3_transform(
                self.translation_min,
                self.translation_max,
                self.rotation_min,
                self.rotation_max,
            )
            if coordinates.shape[-1] == 3:
                coordinates_list[i] = (
                    transform["rotation"] @ coordinates.T
                ).T + transform["translation"]
            elif coordinates.shape[-2] == 3:
                coordinates_list[i] = (
                    transform["rotation"] @ coordinates
                ).T + transform["translation"]
            else:
                raise ValueError(
                    f"Invalid shape for coordinates: {coordinates.shape}"
                )
        return coordinates_list


class ApplySO3Transform(ApplySE3Transform):
    """Applies a given SO3 Transform to the data."""

    def __call__(
        self, coordinates_list: list[NDArrayFloat]
    ) -> list[NDArrayFloat]:
        """Applies a given SO3 Transform to the data."""
        for i, coordinates in enumerate(coordinates_list):
            transform = _gen_random_se3_transform(
                self.translation_min,
                self.translation_max,
                self.rotation_min,
                self.rotation_max,
            )["rotation"]
            if coordinates.shape[-1] == 3:
                coordinates_list[i] = (transform @ coordinates.T).T
            elif coordinates.shape[-2] == 3:
                coordinates_list[i] = (transform @ coordinates).T
            else:
                raise ValueError(
                    f"Invalid shape for coordinates: {coordinates.shape}"
                )
        return coordinates_list


@Transform(in_keys=K.points3d, out_keys=K.points3d)
class TransposeChannels:
    """Transposes some predifined channels."""

    def __init__(self, channels: tuple[int, int] = (-1, -2)):
        """Creates an instance of the class.

        Args:
            channels (tuple[int, int]): Tuple of channels to transpose
        """
        self.channels = channels

    def __call__(
        self, coordinates_list: list[NDArrayFloat]
    ) -> list[NDArrayFloat]:
        """Transposes some predifined channels."""
        for i, coordinates in enumerate(coordinates_list):
            coordinates_list[i] = coordinates.transpose(*self.channels)
        return coordinates_list
