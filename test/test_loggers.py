import argparse
import os.path
import tempfile
from time import sleep

import pytest
import torch
from torchrl.trainers.loggers.csv import CSVLogger
from torchrl.trainers.loggers.tensorboard import TensorboardLogger, _has_tb
from torchrl.trainers.loggers.wandb import WandbLogger, _has_wandb


@pytest.mark.skipif(not _has_tb, reason="TensorBoard not installed")
class TestTensorboard:
    @pytest.mark.parametrize("steps", [None, [1, 10, 11]])
    def test_log_scalar(self, steps):
        torch.manual_seed(0)
        with tempfile.TemporaryDirectory() as log_dir:
            exp_name = "ramala"
            logger = TensorboardLogger(log_dir=log_dir, exp_name=exp_name)

            values = torch.rand(3)
            for i in range(3):
                scalar_name = "foo"
                scalar_value = values[i].item()
                logger.log_scalar(
                    value=scalar_value,
                    name=scalar_name,
                    step=steps[i] if steps else None,
                )

            sleep(0.01)  # wait until events are registered
            from tensorboard.backend.event_processing.event_accumulator import (
                EventAccumulator,
            )

            event_acc = EventAccumulator(logger.experiment.get_logdir())
            event_acc.Reload()
            assert len(event_acc.Scalars("foo")) == 3, str(event_acc.Scalars("foo"))
            for i in range(3):
                assert event_acc.Scalars("foo")[i].value == values[i]
                if steps:
                    assert event_acc.Scalars("foo")[i].step == steps[i]

    @pytest.mark.parametrize("steps", [None, [1, 10, 11]])
    def test_log_video(self, steps):
        torch.manual_seed(0)
        with tempfile.TemporaryDirectory() as log_dir:
            exp_name = "ramala"
            logger = TensorboardLogger(log_dir=log_dir, exp_name=exp_name)

            # creating a sample video (T, C, H, W), where T - number of frames,
            # C - number of image channels (e.g. 3 for RGB), H, W - image dimensions.
            # the first 64 frames are black and the next 64 are white
            video = torch.cat(
                (torch.zeros(64, 1, 32, 32), torch.full((64, 1, 32, 32), 255))
            )
            video = video[None, :]
            for i in range(3):
                logger.log_video(
                    name="foo",
                    video=video,
                    step=steps[i] if steps else None,
                    fps=6,  # we can't test for the difference between fps, because the result is an encoded_string
                )

            sleep(0.01)  # wait until events are registered
            from tensorboard.backend.event_processing.event_accumulator import (
                EventAccumulator,
            )

            event_acc = EventAccumulator(logger.experiment.get_logdir())
            event_acc.Reload()
            assert len(event_acc.Images("foo")) == 3, str(event_acc.Images("foo"))

            # check that we catch the error in case the format of the tensor is wrong
            # here the number of color channels is set to 2, which is not correct
            video_wrong_format = torch.zeros(64, 2, 32, 32)
            video_wrong_format = video_wrong_format[None, :]
            with pytest.raises(Exception):
                logger.log_video(
                    name="foo",
                    video=video_wrong_format,
                    step=steps[i] if steps else None,
                )


class TestCSVLogger:
    @pytest.mark.parametrize("steps", [None, [1, 10, 11]])
    def test_log_scalar(self, steps):
        torch.manual_seed(0)
        with tempfile.TemporaryDirectory() as log_dir:
            exp_name = "ramala"
            logger = CSVLogger(log_dir=log_dir, exp_name=exp_name)

            values = torch.rand(3)
            for i in range(3):
                scalar_name = "foo"
                scalar_value = values[i].item()
                logger.log_scalar(
                    value=scalar_value,
                    name=scalar_name,
                    step=steps[i] if steps else None,
                )

            with open(
                os.path.join(log_dir, exp_name, "scalars", "foo.csv"), "r"
            ) as file:
                for i, row in enumerate(file.readlines()):
                    step = steps[i] if steps else i
                    assert row == f"{step},{values[i].item()}\n"

    @pytest.mark.parametrize("steps", [None, [1, 10, 11]])
    def test_log_video(self, steps):
        torch.manual_seed(0)
        with tempfile.TemporaryDirectory() as log_dir:
            exp_name = "ramala"
            logger = CSVLogger(log_dir=log_dir, exp_name=exp_name)

            # creating a sample video (T, C, H, W), where T - number of frames,
            # C - number of image channels (e.g. 3 for RGB), H, W - image dimensions.
            # the first 64 frames are black and the next 64 are white
            video = torch.cat(
                (torch.zeros(64, 1, 32, 32), torch.full((64, 1, 32, 32), 255))
            )
            video = video[None, :]
            for i in range(3):
                logger.log_video(
                    name="foo",
                    video=video,
                    step=steps[i] if steps else None,
                )
            sleep(0.01)  # wait until events are registered

            # check that the logged videos are the same as the initial video
            video_file_name = "foo_" + ("0" if not steps else str(steps[0])) + ".pt"
            logged_video = torch.load(
                os.path.join(log_dir, exp_name, "videos", video_file_name)
            )
            assert torch.equal(video, logged_video), logged_video

            # check that we catch the error in case the format of the tensor is wrong
            video_wrong_format = torch.zeros(64, 2, 32, 32)
            video_wrong_format = video_wrong_format[None, :]
            with pytest.raises(Exception):
                logger.log_video(
                    name="foo",
                    video=video_wrong_format,
                    step=steps[i] if steps else None,
                )


@pytest.mark.skipif(not _has_wandb, reason="Wandb not installed")
class TestWandbLogger:
    @pytest.mark.parametrize("steps", [None, [1, 10, 11]])
    def test_log_scalar(self, steps):
        torch.manual_seed(0)
        with tempfile.TemporaryDirectory() as log_dir:
            exp_name = "ramala"
            logger = WandbLogger(log_dir=log_dir, exp_name=exp_name, offline=True)

            values = torch.rand(3)
            for i in range(3):
                scalar_name = "foo"
                scalar_value = values[i].item()
                logger.log_scalar(
                    value=scalar_value,
                    name=scalar_name,
                    step=steps[i] if steps else None,
                )

            assert logger.experiment.summary["foo"] == values[-1].item()
            assert logger.experiment.summary["_step"] == i if not steps else steps[i]

            logger.experiment.finish()
            del logger

    def test_log_video(self):
        torch.manual_seed(0)
        with tempfile.TemporaryDirectory() as log_dir:
            exp_name = "ramala"
            logger = WandbLogger(log_dir=log_dir, exp_name=exp_name, offline=True)

            # creating a sample video (T, C, H, W), where T - number of frames,
            # C - number of image channels (e.g. 3 for RGB), H, W - image dimensions.
            # the first 64 frames are black and the next 64 are white
            video = torch.cat(
                (torch.zeros(64, 1, 32, 32), torch.full((64, 1, 32, 32), 255))
            )
            video = video[None, :]
            logger.log_video(
                name="foo",
                video=video,
                fps=6,
            )
            logger.log_video(
                name="foo_12fps",
                video=video,
                fps=24,
            )
            sleep(0.01)  # wait until events are registered

            # check that fps can be passed and that it has impact on the length of the video
            video_6fps_size = logger.experiment.summary["foo"]["size"]
            video_24fps_size = logger.experiment.summary["foo_12fps"]["size"]
            assert video_6fps_size > video_24fps_size, video_6fps_size

            # check that we catch the error in case the format of the tensor is wrong
            video_wrong_format = torch.zeros(64, 2, 32, 32)
            video_wrong_format = video_wrong_format[None, :]
            with pytest.raises(Exception):
                logger.log_video(
                    name="foo",
                    video=video_wrong_format,
                )

            logger.experiment.finish()
            del logger


if __name__ == "__main__":
    args, unknown = argparse.ArgumentParser().parse_known_args()
    pytest.main([__file__, "--capture", "no", "--exitfirst"] + unknown)
