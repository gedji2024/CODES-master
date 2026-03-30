"""Training and evaluation orchestration for MARL algorithms (QMIX, QTRAN).

Key functions:
    run()                 - Top-level entry called by main.py via Sacred.
    run_sequential()      - Main training loop: collect episodes, train, periodically test & save.
    evaluate_sequential() - Load a checkpoint and run test_nepisode eval episodes.

The training loop supports both EpisodeRunner (batch_size_run=1) and ParallelRunner
(batch_size_run>1). When using ParallelRunner, gradient updates are scaled by
batch_size_run to maintain the same update-to-data ratio.
"""
import datetime
import os
import pprint
import time
import threading
import torch as th
from types import SimpleNamespace as SN
from utils.logging import Logger
from utils.timehelper import time_left, time_str
from os.path import dirname, abspath

from learners import REGISTRY as le_REGISTRY
from runners import REGISTRY as r_REGISTRY
from controllers import REGISTRY as mac_REGISTRY
from components.episode_buffer import ReplayBuffer
from components.transforms import OneHot


def run(_run, _config, _log):

    # check args sanity
    _config = args_sanity_check(_config, _log)

    args = SN(**_config)
    if args.use_cuda:
        args.device = "cuda"
        # Log multi-GPU assignment if CUDA_VISIBLE_DEVICES is set by run_algos.ps1
        cvd = os.environ.get("CUDA_VISIBLE_DEVICES", "all")
        _log.info(f"CUDA device selected (CUDA_VISIBLE_DEVICES={cvd}, "
                   f"device_count={th.cuda.device_count()})")
    elif getattr(args, 'use_mps', False) and th.backends.mps.is_available():
        args.device = "mps"
        # Ensure MPS memory allocation is configured for multi-process sharing.
        # Ratio is a multiplier (default HIGH=1.7, LOW=1.0); 0.0 disables the limit.
        if not os.environ.get("PYTORCH_MPS_HIGH_WATERMARK_RATIO"):
            os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"
            os.environ["PYTORCH_MPS_LOW_WATERMARK_RATIO"] = "0.0"
        _log.info(f"MPS device selected (watermark ratio: {os.environ.get('PYTORCH_MPS_HIGH_WATERMARK_RATIO')})")
    else:
        args.device = "cpu"

    # setup loggers
    logger = Logger(_log)

    _log.info("Experiment Parameters:")
    experiment_params = pprint.pformat(_config, indent=4, width=1)
    _log.info("\n\n" + experiment_params + "\n")

    try:
        map_name = _config["env_args"]["map_name"]
    except:
        map_name = _config["env_args"]["key"]
    unique_token = f"{_config['name']}_seed{_config['seed']}_{map_name}_{datetime.datetime.now()}"

    args.unique_token = unique_token
    if args.use_tensorboard:
        tb_logs_direc = os.path.join(
            dirname(dirname(abspath(__file__))), "results", "tb_logs"
        )
        tb_exp_direc = os.path.join(tb_logs_direc, "{}").format(unique_token)
        logger.setup_tb(tb_exp_direc)

    # sacred is on by default
    logger.setup_sacred(_run)

    # Run and train
    run_sequential(args=args, logger=logger)

    # Clean up after finishing
    print("Exiting Main")

    print("Stopping all threads")
    for t in threading.enumerate():
        if t.name != "MainThread":
            print("Thread {} is alive! Is daemon: {}".format(t.name, t.daemon))
            t.join(timeout=1)
            print("Thread joined")

    print("Exiting script")

    # Making sure framework really exits
    # os._exit(os.EX_OK)


def evaluate_sequential(args, runner):
    # With parallel runner each run() produces batch_size episodes,
    # so divide the loop count to get the requested total.
    batch_size = getattr(runner, 'batch_size', 1)
    n_runs = max(1, args.test_nepisode // batch_size)
    for _ in range(n_runs):
        runner.run(test_mode=True)

    if args.save_replay:
        runner.save_replay()

    runner.close_env()


def run_sequential(args, logger):
    # Init runner so we can get env info
    runner = r_REGISTRY[args.runner](args=args, logger=logger)
    
    # Set up schemes and groups here
    env_info = runner.get_env_info()
    args.n_agents = env_info["n_agents"]
    args.n_actions = env_info["n_actions"]
    args.state_shape = env_info["state_shape"]
    
    # Default/Base scheme
    scheme = {
        "state": {"vshape": env_info["state_shape"]},
        "obs": {"vshape": env_info["obs_shape"], "group": "agents"},
        "actions": {"vshape": (1,), "group": "agents", "dtype": th.long},
        "avail_actions": {
            "vshape": (env_info["n_actions"],),
            "group": "agents",
            "dtype": th.int,
        },
        "reward": {"vshape": (1,)},
        "terminated": {"vshape": (1,), "dtype": th.uint8},
    }
    
    groups = {"agents": args.n_agents}
    
    preprocess = {"actions": ("actions_onehot", [OneHot(out_dim=args.n_actions)])}
    
    buffer = ReplayBuffer(
        scheme,
        groups,
        args.buffer_size,
        env_info["episode_limit"] + 1,
        preprocess=preprocess,
        device="cpu" if args.buffer_cpu_only else args.device,
    )
    
    # Setup multiagent controller here
    mac = mac_REGISTRY[args.mac](buffer.scheme, groups, args)
    
    # Give runner the scheme
    runner.setup(scheme=scheme, groups=groups, preprocess=preprocess, mac=mac)

    # Learner
    learner = le_REGISTRY[args.learner](mac, buffer.scheme, logger, args)
    
    if args.device != "cpu":
        if hasattr(learner, 'to_device'):
            learner.to_device(args.device)
        else:
            learner.cuda()  # fallback for learners without to_device()

    if args.checkpoint_path != "":

        timesteps = []
        timestep_to_load = 0

        if not os.path.isdir(args.checkpoint_path):
            logger.console_logger.info(
                "Checkpoint directiory {} doesn't exist".format(args.checkpoint_path)
            )
            return

        # Go through all files in args.checkpoint_path
        for name in os.listdir(args.checkpoint_path):
            full_name = os.path.join(args.checkpoint_path, name)
            # Check if they are dirs the names of which are numbers
            if os.path.isdir(full_name) and name.isdigit():
                timesteps.append(int(name))

        if args.load_step == 0:
            # choose the max timestep
            timestep_to_load = max(timesteps)
        else:
            # choose the timestep closest to load_step
            timestep_to_load = min(timesteps, key=lambda x: abs(x - args.load_step))

        model_path = os.path.join(args.checkpoint_path, str(timestep_to_load))

        logger.console_logger.info("Loading model from {}".format(model_path))
        learner.load_models(model_path)
        runner.t_env = timestep_to_load

        if args.evaluate or args.save_replay:
            runner.log_train_stats_t = runner.t_env
            evaluate_sequential(args, runner)
            logger.log_stat("episode", runner.t_env, runner.t_env)
            logger.print_recent_stats()
            logger.console_logger.info("Finished Evaluation")
            return

    # start training
    episode = 0
    last_test_T = -args.test_interval - 1
    last_log_T = 0
    model_save_time = 0

    start_time = time.time()
    last_time = start_time

    logger.console_logger.info("Beginning training for {} timesteps".format(args.t_max))

    while runner.t_env <= args.t_max:

        # Run for a whole episode at a time
        episode_batch = runner.run(test_mode=False)
        buffer.insert_episode_batch(episode_batch)

        # With parallel runner (batch_size_run > 1), each run() collects
        # multiple episodes but the loop body executes once.  Train
        # batch_size_run times to maintain the same gradient-update-to-data
        # ratio as the episode runner.
        n_train_steps = getattr(args, "batch_size_run", 1)
        for _train_i in range(n_train_steps):
            if buffer.can_sample(args.batch_size):
                episode_sample = buffer.sample(args.batch_size)

                # Truncate batch to only filled timesteps
                max_ep_t = episode_sample.max_t_filled()
                if max_ep_t == 0:
                    break
                episode_sample = episode_sample[:, :max_ep_t]

                if episode_sample.device != args.device:
                    episode_sample.to(args.device)

                learner.train(episode_sample, runner.t_env, episode)

        # Execute test runs once in a while
        n_test_runs = max(1, args.test_nepisode // runner.batch_size)
        if (runner.t_env - last_test_T) / args.test_interval >= 1.0:

            logger.console_logger.info(
                "t_env: {} / {}".format(runner.t_env, args.t_max)
            )
            logger.console_logger.info(
                "Estimated time left: {}. Time passed: {}".format(
                    time_left(last_time, last_test_T, runner.t_env, args.t_max),
                    time_str(time.time() - start_time),
                )
            )
            last_time = time.time()

            last_test_T = runner.t_env
            for _ in range(n_test_runs):
                runner.run(test_mode=True)

        if args.save_model and (
            runner.t_env - model_save_time >= args.save_model_interval
            or model_save_time == 0
        ):
            model_save_time = runner.t_env
            save_path = os.path.join(
                args.local_results_path, "models", args.unique_token, str(runner.t_env)
            )
            # "results/models/{}".format(unique_token)
            valid_save_path = save_path.replace(":", "_")
            os.makedirs(valid_save_path, exist_ok=True)
            logger.console_logger.info("Saving models to {}".format(valid_save_path))

            # learner should handle saving/loading -- delegate actor save/load to mac,
            # use appropriate filenames to do critics, optimizer states
            learner.save_models(valid_save_path)

        episode += args.batch_size_run

        if (runner.t_env - last_log_T) >= args.log_interval:
            logger.log_stat("episode", episode, runner.t_env)
            logger.print_recent_stats()
            last_log_T = runner.t_env

    # --- End-of-training model save (guarantees eval pass has a fully-trained checkpoint) ---
    if args.save_model:
        save_path = os.path.join(
            args.local_results_path, "models", args.unique_token, str(runner.t_env)
        )
        valid_save_path = save_path.replace(":", "_")
        os.makedirs(valid_save_path, exist_ok=True)
        logger.console_logger.info("Saving final models to {}".format(valid_save_path))
        learner.save_models(valid_save_path)

    runner.close_env()
    logger.console_logger.info("Finished Training")


def args_sanity_check(config, _log):

    # set CUDA flags
    # config["use_cuda"] = True # Use cuda whenever possible!
    if config["use_cuda"] and not th.cuda.is_available():
        config["use_cuda"] = False
        _log.warning(
            "CUDA flag use_cuda was switched OFF automatically because no CUDA devices are available!"
        )

    # set MPS flags (Apple Silicon GPU)
    if config.get("use_mps", False) and not (hasattr(th.backends, 'mps') and th.backends.mps.is_available()):
        config["use_mps"] = False
        _log.warning(
            "MPS flag use_mps was switched OFF automatically because no MPS devices are available!"
        )
    elif config.get("use_mps", False) and not config["use_cuda"]:
        _log.info("Using Apple Silicon GPU (MPS) for acceleration")

    if config["test_nepisode"] < config["batch_size_run"]:
        config["test_nepisode"] = config["batch_size_run"]
    else:
        config["test_nepisode"] = (
            config["test_nepisode"] // config["batch_size_run"]
        ) * config["batch_size_run"]

    return config
