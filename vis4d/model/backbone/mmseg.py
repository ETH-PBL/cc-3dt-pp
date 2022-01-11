"""mmdetection backbone wrapper."""
from typing import Optional

try:
    from mmcv.runner import BaseModule
    from mmcv.runner.checkpoint import load_checkpoint

    MMCV_INSTALLED = True
except (ImportError, NameError):  # pragma: no cover
    MMCV_INSTALLED = False

try:
    from mmseg.models import build_backbone

    MMSEG_INSTALLED = True
except (ImportError, NameError):  # pragma: no cover
    MMSEG_INSTALLED = False

from vis4d.struct import (
    DictStrAny,
    FeatureMaps,
    Images,
    InputSample,
    SemanticMasks,
)

from .base import BaseBackbone, BaseBackboneConfig
from .neck import BaseNeck, build_neck

MMSEG_MODEL_PREFIX = "https://download.openmmlab.com/mmsegmentation/v0.5/"


class MMSegBackboneConfig(BaseBackboneConfig):
    """Config for mmseg backbones."""

    mm_cfg: DictStrAny
    weights: Optional[str]


class MMSegBackbone(BaseBackbone):
    """mmsegmentation backbone wrapper."""

    def __init__(self, cfg: BaseBackboneConfig):
        """Init."""
        assert (
            MMSEG_INSTALLED and MMCV_INSTALLED
        ), "MMSegBackbone requires both mmcv and mmseg to be installed!"
        super().__init__(cfg)
        self.cfg: MMSegBackboneConfig = MMSegBackboneConfig(**cfg.dict())
        self.mm_backbone = build_backbone(self.cfg.mm_cfg)
        assert isinstance(self.mm_backbone, BaseModule)
        self.mm_backbone.init_weights()
        self.mm_backbone.train()

        self.neck: Optional[BaseNeck] = None
        if self.cfg.neck is not None:
            self.neck = build_neck(self.cfg.neck)

        if self.cfg.weights is not None:  # pragma: no cover
            if self.cfg.weights.startswith("mmseg://"):
                self.cfg.weights = (
                    MMSEG_MODEL_PREFIX + self.cfg.weights.split("mmseg://")[-1]
                )
            load_checkpoint(self.mm_backbone, self.cfg.weights)

    def preprocess_inputs(self, inputs: InputSample) -> InputSample:
        """Normalize the input images, pad masks."""
        if not self.training:
            # no padding during inference to match MMSegmentation
            Images.stride = 1
        super().preprocess_inputs(inputs)
        if self.training and len(inputs.targets.semantic_masks) > 1:
            # pad masks to same size for batching
            inputs.targets.semantic_masks = SemanticMasks.pad(
                inputs.targets.semantic_masks,
                inputs.images.tensor.shape[-2:][::-1],
            )
        return inputs

    def __call__(  # type: ignore[override]
        self, inputs: InputSample
    ) -> FeatureMaps:
        """Backbone forward.

        Args:
            inputs: Model Inputs, batched.

        Returns:
            FeatureMaps: Dictionary of output feature maps.
        """
        inputs = self.preprocess_inputs(inputs)
        outs = self.mm_backbone(inputs.images.tensor)
        backbone_outs = self.get_outputs(outs)
        if self.neck is not None:
            return self.neck(backbone_outs)
        return backbone_outs
