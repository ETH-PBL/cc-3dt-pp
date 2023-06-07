"""Test cases for evaluator callback."""
import shutil
import tempfile
import unittest

import torch

from tests.util import MockModel, get_test_data
from vis4d.config.common.datasets import CONN_COCO_BBOX_EVAL
from vis4d.data.const import CommonKeys as K
from vis4d.engine.callbacks import EvaluatorCallback, TrainerState
from vis4d.engine.connectors import CallbackConnector
from vis4d.eval.detect.coco import COCOEvaluator


class TestEvaluatorCallback(unittest.TestCase):
    """Test cases for callback functions."""

    def setUp(self) -> None:
        """Creates a tmp directory and setup callback."""
        self.test_dir = tempfile.mkdtemp()

        self.callback = EvaluatorCallback(
            evaluator=COCOEvaluator(
                data_root=get_test_data("coco_test"), split="train"
            ),
            save_predictions=True,
            save_prefix=self.test_dir,
            test_connector=CallbackConnector(CONN_COCO_BBOX_EVAL),
        )

        self.callback.setup()

        self.trainer_state = TrainerState(
            current_epoch=0,
            num_epochs=0,
            global_step=0,
            train_dataloader=None,
            num_train_batches=None,
            test_dataloader=None,
            num_test_batches=None,
        )

    def tearDown(self) -> None:
        """Removes the tmp directory after the test."""
        shutil.rmtree(self.test_dir)

    def test_on_test_batch_end(self) -> None:
        """Test on_test_batch_end function."""
        self.callback.on_test_batch_end(
            self.trainer_state,
            MockModel(0),
            outputs={
                "boxes": [torch.zeros((0, 4))],
                "scores": [torch.zeros((0, 1))],
                "class_ids": [torch.zeros((0, 1))],
            },
            batch={K.sample_names: [0]},
            batch_idx=0,
        )

    def test_on_test_epoch_end(self) -> None:
        """Test on_test_epoch_end function."""
        self.callback.on_test_epoch_end(self.trainer_state, MockModel(0))