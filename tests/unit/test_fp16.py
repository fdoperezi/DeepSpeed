import torch
import deepspeed
import argparse
import pytest
import json
import os
from common import distributed_test
from simple_model import SimpleModel, SimpleOptimizer, random_dataloader, args_from_dict


def test_lamb_fp16_basic(tmpdir):
    config_dict = {
        "train_batch_size": 2,
        "steps_per_print": 1,
        "optimizer": {
            "type": "Lamb",
            "params": {
                "lr": 0.00015,
                "max_grad_norm": 1.0
            }
        },
        "fp16": {
            "enabled": True
        }
    }
    args = args_from_dict(tmpdir, config_dict)
    hidden_dim = 10

    model = SimpleModel(hidden_dim, empty_grad=False)

    @distributed_test(world_size=[1, 2])
    def _test_lamb_fp16_basic(args, model, hidden_dim):
        model, _, _,_ = deepspeed.initialize(args=args,
                                             model=model,
                                             model_parameters=model.parameters())
        data_loader = random_dataloader(model=model,
                                        total_samples=50,
                                        hidden_dim=hidden_dim,
                                        device=model.device)
        for n, batch in enumerate(data_loader):
            loss = model(batch[0], batch[1])
            model.backward(loss)
            model.step()

    _test_lamb_fp16_basic(args=args, model=model, hidden_dim=hidden_dim)


def test_lamb_fp16_empty_grad(tmpdir):
    config_dict = {
        "train_batch_size": 1,
        "steps_per_print": 1,
        "optimizer": {
            "type": "Lamb",
            "params": {
                "lr": 0.00015,
                "max_grad_norm": 1.0
            }
        },
        "fp16": {
            "enabled": True
        }
    }
    args = args_from_dict(tmpdir, config_dict)
    hidden_dim = 10

    model = SimpleModel(hidden_dim, empty_grad=True)

    @distributed_test(world_size=[1])
    def _test_lamb_fp16_empty_grad(args, model, hidden_dim):
        model, _, _,_ = deepspeed.initialize(args=args,
                                             model=model,
                                             model_parameters=model.parameters())
        data_loader = random_dataloader(model=model,
                                        total_samples=50,
                                        hidden_dim=hidden_dim,
                                        device=model.device)
        for n, batch in enumerate(data_loader):
            loss = model(batch[0], batch[1])
            model.backward(loss)
            model.step()

    _test_lamb_fp16_empty_grad(args=args, model=model, hidden_dim=hidden_dim)


def test_adamw_fp16_basic(tmpdir):
    config_dict = {
        "train_batch_size": 1,
        "steps_per_print": 1,
        "fp16": {
            "enabled": True
        }
    }
    args = args_from_dict(tmpdir, config_dict)
    hidden_dim = 10

    model = SimpleModel(hidden_dim, empty_grad=False)

    @distributed_test(world_size=[1])
    def _test_adamw_fp16_basic(args, model, hidden_dim):
        optimizer = torch.optim.AdamW(params=model.parameters())
        model, _, _,_ = deepspeed.initialize(args=args,
                                             model=model,
                                             optimizer=optimizer)
        data_loader = random_dataloader(model=model,
                                        total_samples=50,
                                        hidden_dim=hidden_dim,
                                        device=model.device)
        for n, batch in enumerate(data_loader):
            loss = model(batch[0], batch[1])
            model.backward(loss)
            model.step()

    _test_adamw_fp16_basic(args=args, model=model, hidden_dim=hidden_dim)


def test_adamw_fp16_empty_grad(tmpdir):
    config_dict = {
        "train_batch_size": 1,
        "steps_per_print": 1,
        "fp16": {
            "enabled": True
        }
    }
    args = args_from_dict(tmpdir, config_dict)
    hidden_dim = 10

    model = SimpleModel(hidden_dim, empty_grad=True)

    @distributed_test(world_size=[1])
    def _test_adamw_fp16_empty_grad(args, model, hidden_dim):
        optimizer = torch.optim.AdamW(params=model.parameters())
        model, _, _,_ = deepspeed.initialize(args=args,
                                             model=model,
                                             optimizer=optimizer)
        data_loader = random_dataloader(model=model,
                                        total_samples=50,
                                        hidden_dim=hidden_dim,
                                        device=model.device)
        for n, batch in enumerate(data_loader):
            loss = model(batch[0], batch[1])
            model.backward(loss)
            model.step()

    _test_adamw_fp16_empty_grad(args=args, model=model, hidden_dim=hidden_dim)


@pytest.mark.parametrize("zero_stage", [0, 1, 2])
def test_adam_fp16_zero_onecycle_compatibility(tmpdir, zero_stage):
    config_dict = {
        "train_batch_size": 1,
        "steps_per_print": 1,
        "optimizer": {
            "type": "Adam",
            "params": {
                "lr": 0.00015
            }
        },
        "scheduler": {
            "type": "OneCycle",
            "params": {
                "cycle_first_step_size": 16000,
                "cycle_first_stair_count": 8000,
                "decay_step_size": 16000,
                "cycle_min_lr": 1e-06,
                "cycle_max_lr": 3e-05,
                "decay_lr_rate": 1e-07,
                "cycle_min_mom": 0.85,
                "cycle_max_mom": 0.99,
                "decay_mom_rate": 0.0
            }
        },
        "fp16": {
            "enabled": True
        },
        "zero_optimization": {
            "stage": zero_stage
        }
    }

    args = args_from_dict(tmpdir, config_dict)
    hidden_dim = 10

    model = SimpleModel(hidden_dim, empty_grad=True)

    @distributed_test(world_size=[1])
    def _test_adam_fp16_zero_onecycle_compatibility(args, model, hidden_dim):
        model, _, _,_ = deepspeed.initialize(args=args,
                                             model=model,
                                             model_parameters=model.parameters())
        data_loader = random_dataloader(model=model,
                                        total_samples=50,
                                        hidden_dim=hidden_dim,
                                        device=model.device)
        for n, batch in enumerate(data_loader):
            loss = model(batch[0], batch[1])
            model.backward(loss)
            model.step()

    _test_adam_fp16_zero_onecycle_compatibility(args=args,
                                                model=model,
                                                hidden_dim=hidden_dim)


@pytest.mark.parametrize("zero_stage", [1, 2])
def test_zero_static_scale(tmpdir, zero_stage):
    config_dict = {
        "train_batch_size": 4,
        "steps_per_print": 1,
        "optimizer": {
            "type": "Adam",
            "params": {
                "lr": 0.00015
            }
        },
        "fp16": {
            "enabled": True,
            "loss_scale": 138.
        },
        "zero_optimization": {
            "stage": zero_stage
        }
    }
    args = args_from_dict(tmpdir, config_dict)

    @distributed_test(world_size=2)
    def _test_zero_static_scale(args):
        hidden_dim = 10
        model = SimpleModel(hidden_dim, empty_grad=True)
        model, optim, _,_ = deepspeed.initialize(args=args,
                                            model=model,
                                            model_parameters=model.parameters())

        # Ensure the static scaler is configured.
        assert optim.dynamic_loss_scale == False
        assert optim.loss_scaler.loss_scale == 138.

        # Now make sure things work..
        data_loader = random_dataloader(model=model,
                                        total_samples=10,
                                        hidden_dim=hidden_dim,
                                        device=model.device)
        for n, batch in enumerate(data_loader):
            loss = model(batch[0], batch[1])
            model.backward(loss)
            model.step()

    _test_zero_static_scale(args)


@pytest.mark.parametrize("zero_stage", [1, 2])
def test_zero_allow_untested_optimizer(tmpdir, zero_stage):
    config_dict = {
        "train_batch_size": 4,
        "steps_per_print": 1,
        "fp16": {
            "enabled": True,
        },
        "zero_optimization": {
            "stage": zero_stage
        },
        "zero_allow_untested_optimizer": False
    }
    args = args_from_dict(tmpdir, config_dict)

    @distributed_test(world_size=[1])
    def _test_zero_allow_untested_optimizer(args):
        hidden_dim = 10
        model = SimpleModel(hidden_dim, empty_grad=True)
        optimizer = SimpleOptimizer(model.parameters())
        with pytest.raises(AssertionError):
            model, optim, _,_ = deepspeed.initialize(args=args,
                                                    model=model,
                                                    optimizer=optimizer,
                                                    model_parameters=model.parameters())

    _test_zero_allow_untested_optimizer(args)


@pytest.mark.parametrize("zero_stage", [1])
def test_zero_empty_partition(tmpdir, zero_stage):
    config_dict = {
        "train_batch_size": 3,
        "fp16": {
            "enabled": True
        },
        "optimizer": {
            "type": "Adam",
            "params": {
                "lr": 0.00015
            }
        },
        "zero_optimization": {
            "stage": zero_stage
        }
    }
    args = args_from_dict(tmpdir, config_dict)

    @distributed_test(world_size=[3])
    def _test_zero_empty_partition(args):
        hidden_dim = 1
        model = SimpleModel(hidden_dim)
        # Ensure model has 2 parameters, to cause empty partition with DP=3
        assert len(list(model.parameters())) == 2
        model, _, _, _ = deepspeed.initialize(args=args,
                                              model=model,
                                              model_parameters=model.parameters())
        model.step()

    _test_zero_empty_partition(args)
