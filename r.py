# r.py - lazy launcher entry point
import argparse
import asyncio
import sys
import os
from pathlib import Path

# Import the actual launcher
from runtime.legacy.launcher import main

import threading

async def debug_input():
    """Debug input for testing"""
    print("\n🦊 DEBUG: Type 'hello' or press Enter to test input...")
    loop = asyncio.get_event_loop()
    while True:
        try:
            line = await loop.run_in_executor(None, input, ">>> ")
            if line.strip():
                print(f"📥 GOT INPUT: {line}")
                # This would trigger orchestrator input
        except EOFError:
            break
        except KeyboardInterrupt:
            break

# Force stdin to be line-buffered
sys.stdin.reconfigure(encoding='utf-8', errors='ignore')
os.environ['PYTHONUNBUFFERED'] = '1'

LOGO = r""" 
=============================||=============================


                ░\                        /░
             /░/  ░\                    /░  \░\
           /░/      \░\              /░/      \░\
           ░/         \░\          /░/         \░
         /░░           \░\        /░/           ░░\
        /░░             \░\      /░/             ░░\
        ░░     /░░░░\    ░░\____/░░    /░░░░\     ░░
        ░░    |░░░░░░░ /░░/░░||░░\░░\ ░░░░░░░|    ░░
        ░░   /░░░░░░░░░░░░░_=┘└=_░░░░░░░░░░░░░\   ░░
        \░░  |░░░/░░░░░░░//      \\░░░░░░░░\░░|  ░░/
         \░░/░░░░░░__░░░||        ||░░░__░░░░░░\░░/
          \░░░░░░/1010\_░\\      //░_/0010\░░░░░░/
          /░░\░░░░\0101_\░░¯=┐┌=¯░░/_0010/░░░░/░░\
          ░░_\¯\\_░░░░░░¯\░░░||░░░/¯░░░░░░_//¯/_░░
        /░░/10\   ¯\░░░░░░░░░||░░░░░░░░░/¯   /01\░░\
        ░░░\010\     ¯\░░░░░░||░░░░░░/¯     /010/░░░
       ░░\░░¯001¯\_     \░░░░||░░░░/     _/¯011¯░░/░░
       ░|11\░░░░¯\0=¯ = _ \░░||░░/ _ = ¯=1/¯░░░░/01|░
       \░░0101\░░░░░░░░░░░'░░||░░'░░░░░░░░░░░/0100░░/
        \░░\0010░░░_101\░░░░░||░░░░░/110_░░░1010/░░/
          \_░░░░░_/101/░░░/░░||░░\░░░\010\_░░░░░_/
             ¯\\_░░░░░░░░/|░░||░░|\░░░░░░░__//¯
                 ¯\\_░░░░\ ¯¯  ¯¯ /░░░░░//¯
                      \░░░░░░¯¯░░░░░░░/
                       \░░░░░||░░░░░/ 
                         ¯¯==--==¯¯

=============================||=============================
"""



def parse_args():
    parser = argparse.ArgumentParser(prog="r.py")

    parser.add_argument(
        "--model",
        nargs="*",
        metavar=("MODEL", "COUNT|lock"),
        help="Override model temporarily or permanently"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (shows debug logs)"
    )

    parser.add_argument(
        "--logo",
        action="store_true",
        help="only show logo wont start launcher"
    )

    parser.add_argument(
        "--safe",
        action="store_true",
        help="Force ultra low safe-mode profile"
    )

    parser.add_argument(
        "--first-run",
        action="store_true", 
        help="Run first-run setup and exit"
    )

    parser.add_argument(
        "--profile",
        type=str,
        help="Force a specific hardware profile"
    )

    parser.add_argument(
        "--training-dataset",
        type=str,
        metavar="DATASET_PATH",
        help="Specify path to training dataset file"
    )

    parser.add_argument(
        "--bootstrap-only",
        action="store_true",
        help="Run bootstrap only and exit"
    )

    parser.add_argument(
        "--test-mode",
        action="store_true", 
        help="Run in quick test mode"
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show module status and exit"
    )

    args = parser.parse_args()
    overrides = {}
    
    # Store logo flag in overrides
    if args.logo:
        overrides["logo"] = True
    
    # Store debug flag in overrides for launcher
    if args.debug:
        overrides["debug"] = True
    
    # Store safe flag in overrides for launcher
    if args.safe:
        overrides["safe"] = True
    
    # Store first-run flag in overrides for launcher
    if args.first_run:
        overrides["first_run"] = True
    
    # Store profile flag in overrides for launcher
    if args.profile:
        overrides["profile"] = args.profile
    
    # Store training dataset in overrides
    if args.training_dataset:
        overrides["training_dataset"] = args.training_dataset
    
    # Store bootstrap-only flag in overrides
    if args.bootstrap_only:
        overrides["bootstrap_only"] = True
    
    # Store test-mode flag in overrides
    if args.test_mode:
        overrides["test_mode"] = True
    
    # Store status flag in overrides
    if args.status:
        overrides["status"] = True

    # --model not provided at all
    if args.model is None:
        return overrides

    # --model  → reset
    if len(args.model) == 0:
        overrides["model"] = {
            "action": "reset",
            "value": DEFAULT_MODEL,
        }
        return overrides

    # --model MODEL COUNT|lock
    if len(args.model) == 2:
        model, action = args.model

        if action == "lock":
            overrides["model"] = {
                "action": "lock",
                "value": model,
            }
            return overrides

        try:
            count = int(action)
            overrides["model"] = {
                "action": "temporary",
                "value": model,
                "runs": count,
            }
            return overrides
        except ValueError:
            sys.exit("Error: second argument must be an integer or 'lock'")
    
    # Invalid usage
    sys.exit("Error: invalid --model usage")


if __name__ == "__main__":
    overrides = parse_args()
    if overrides.get("logo"):
        print(LOGO)
        sys.exit(0)
    
    # Handle training dataset separately - don't run runtime loop
    if overrides.get("training_dataset"):
        dataset_path = Path(overrides['training_dataset'])
        print(f"Training dataset specified: {dataset_path}")

        try:
            from runtime.learning.micro_trainer import MicroTrainer
            import json
            import os
        except ImportError as e:
            sys.exit(f"Error importing training modules: {e}")

        trainer = MicroTrainer()
        if not trainer.verify_dataset(str(dataset_path)):
            sys.exit(f"Error: Training dataset failed integrity checks: {dataset_path}")

        try:
            print(f"Loading training data from {dataset_path}...")
            with dataset_path.open('r', encoding='utf-8') as f:
                training_data = json.load(f)

            print("Initializing trainer...")
            print("Training model...")
            results = trainer.train(training_data)

            print("\n=== TRAINING RESULTS ===")
            print(f"Loss: {results.get('loss', 'N/A')}")
            print(f"Accuracy: {results.get('accuracy', 'N/A')}")
            print(f"Epochs completed: {results.get('epochs', 'N/A')}")
            print(f"Training samples: {len(training_data)}")

            if dataset_path.exists():
                print(f"\nRemoving old dataset: {dataset_path}")
                os.remove(dataset_path)
                print("Old dataset removed successfully.")

            print("\nTraining completed successfully!")
        except FileNotFoundError:
            sys.exit(f"Error: Dataset file not found: {dataset_path}")
        except json.JSONDecodeError:
            sys.exit(f"Error: Invalid JSON format in dataset file: {dataset_path}")
        except Exception as e:
            sys.exit(f"Error during training: {e}")

        sys.exit(0)

    # Import launcher for feature flag routing
    from runtime.legacy.launcher import Launcher
    
    # Handle feature flags
    if overrides.get("bootstrap_only"):
        sys.exit(asyncio.run(Launcher.bootstrap()))
    elif overrides.get("test_mode"):
        sys.exit(asyncio.run(Launcher.quick_start()))
    elif overrides.get("status"):
        sys.exit(asyncio.run(Launcher.show_status()))
    else:
        async def main_with_debug():
            # Start debug input task
            debug_task = asyncio.create_task(debug_input())
            try:
                await main()
            finally:
                debug_task.cancel()
                try:
                    await debug_task
                except asyncio.CancelledError:
                    pass
        
        sys.exit(asyncio.run(main_with_debug()))
