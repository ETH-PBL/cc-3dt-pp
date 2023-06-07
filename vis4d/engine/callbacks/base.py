"""Base module for callbacks."""
from __future__ import annotations

from torch import Tensor, nn

from vis4d.common.typing import DictStrArrNested, MetricLogs
from vis4d.data.typing import DictData
from vis4d.engine.connectors import CallbackConnector

from .trainer_state import TrainerState


class Callback:
    """Base class for Callbacks."""

    def __init__(
        self,
        epoch_based: bool = True,
        train_connector: None | CallbackConnector = None,
        test_connector: None | CallbackConnector = None,
    ) -> None:
        """Init callback.

        Args:
            epoch_based (bool, optional): Whether the callback is epoch based.
                Defaults to False.
            train_connector (None | CallbackConnector, optional): Defines which
                kwargs to use during training for different callbacks. Defaults
                to None.
            test_connector (None | CallbackConnector, optional): Defines which
                kwargs to use during testing for different callbacks. Defaults
                to None.
        """
        self.epoch_based = epoch_based
        self.train_connector = train_connector
        self.test_connector = test_connector

    def setup(self) -> None:
        """Setup callback."""

    def get_iteration(
        self,
        trainer_state: TrainerState,
        train: bool,
        batch_idx: int,
        dataloader_idx: int = 0,
    ) -> tuple[int, int]:
        """Returns the current iteration and total iterations."""
        if self.epoch_based or not train:
            cur_iter = batch_idx + 1

            if train:
                total_iters = (
                    trainer_state["num_train_batches"]
                    if trainer_state["num_train_batches"] is not None
                    else -1
                )
            else:
                total_iters = (
                    trainer_state["num_test_batches"][dataloader_idx]
                    if trainer_state["num_test_batches"] is not None
                    else -1
                )
        else:
            cur_iter = trainer_state["global_step"] + 1
            total_iters = trainer_state["num_steps"]

        return cur_iter, total_iters

    def get_train_callback_inputs(
        self, outputs: DictData, batch: DictData
    ) -> dict[str, Tensor | DictStrArrNested]:
        """Returns the data connector results for training.

        It extracts the required data from prediction and datas and passes it
        to the next component with the provided new key.

        Args:
            outputs (DictData): Outputs of the model.
            batch (DictData): Batch data.

        Returns:
            dict[str, Tensor | DictStrArrNested]: Data connector results.

        Raises:
            AssertionError: If train connector is None.
        """
        assert self.train_connector is not None, "Train connector is None."

        return self.train_connector(outputs, batch)

    def get_test_callback_inputs(
        self, outputs: DictData, batch: DictData
    ) -> dict[str, Tensor | DictStrArrNested]:
        """Returns the data connector results for inference.

        It extracts the required data from prediction and datas and passes it
        to the next component with the provided new key.

        Args:
            outputs (DictData): Outputs of the model.
            batch (DictData): Batch data.

        Returns:
            dict[str, Tensor | DictStrArrNested]: Data connector results.

        Raises:
            AssertionError: If test connector is None.
        """
        assert self.test_connector is not None, "Test connector is None."

        return self.test_connector(outputs, batch)

    def on_train_batch_start(
        self,
        trainer_state: TrainerState,
        model: nn.Module,
        batch: DictData,
        batch_idx: int,
    ) -> None:
        """Hook to run at the start of a training batch.

        Args:
            trainer_state (TrainerState): Trainer state.
            model: Model that is being trained.
            batch (DictData): Dataloader output data batch.
            batch_idx (int): Index of the batch.
        """

    def on_train_epoch_start(
        self, trainer_state: TrainerState, model: nn.Module
    ) -> None:
        """Hook to run at the beginning of a training epoch.

        Args:
            trainer_state (TrainerState): Trainer state.
            model (nn.Module): Model that is being trained.
        """

    def on_train_batch_end(
        self,
        trainer_state: TrainerState,
        model: nn.Module,
        outputs: DictData,
        batch: DictData,
        batch_idx: int,
    ) -> None | MetricLogs:
        """Hook to run at the end of a training batch.

        Args:
            trainer_state (TrainerState): Trainer state.
            model: Model that is being trained.
            outputs (DictData): Model prediction output.
            batch (DictData): Dataloader output data batch.
            batch_idx (int): Index of the batch.
        """

    def on_train_epoch_end(
        self, trainer_state: TrainerState, model: nn.Module
    ) -> None:
        """Hook to run at the end of a training epoch.

        Args:
            trainer_state (TrainerState): Trainer state.
            model (nn.Module): Model that is being trained.
        """

    def on_test_epoch_start(
        self, trainer_state: TrainerState, model: nn.Module
    ) -> None:
        """Hook to run at the beginning of a testing epoch.

        Args:
            trainer_state (TrainerState): Trainer state.
            model (nn.Module): Model that is being trained.
        """

    def on_test_batch_end(
        self,
        trainer_state: TrainerState,
        model: nn.Module,
        outputs: DictData,
        batch: DictData,
        batch_idx: int,
        dataloader_idx: int = 0,
    ) -> None:
        """Hook to run at the end of a testing batch.

        Args:
            trainer_state (TrainerState): Trainer state.
            model: Model that is being trained.
            outputs (DictData): Model prediction output.
            batch (DictData): Dataloader output data batch.
            batch_idx (int): Index of the batch.
            dataloader_idx (int, optional): Index of the dataloader. Defaults
                to 0.
        """

    def on_test_epoch_end(
        self, trainer_state: TrainerState, model: nn.Module
    ) -> None | MetricLogs:
        """Hook to run at the end of a testing epoch.

        Args:
            trainer_state (TrainerState): Trainer state.
            model (nn.Module): Model that is being trained.
        """