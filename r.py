# r.py - lazy launcher
import argparse
import sys
from pathlib import Path

from app.launcher import main

DEFAULT_MODEL = "kitsu:character"
LOGO = r"""
=============================||=============================


                ░\                        /░
              /░/ ░\                    /░ \░\
            /░/    \░\                /░/    \░\
           ░/        \░\            /░/        \░
         /░░          \░\          /░/          ░░\
        /░░            \░\        /░/            ░░\
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
       ░░11\░░░¯\10=¯ = _ \░░||░░/ _ = ¯=01/¯░░░/01░░
       \░░\101\░░░░░░░░░░░'░░||░░'░░░░░░░░░░░/010/░░/
        \░░\001░░░░_101\░░░░░||░░░░░/110_░░░░010/░░/
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
        "--training-dataset",
        type=str,
        metavar="DATASET_PATH",
        help="Specify path to training dataset file"
    )

    args = parser.parse_args()
    overrides = {}
    
    # Store logo flag in overrides
    if args.logo:
        overrides["logo"] = True
    
    # Store debug flag in overrides for launcher
    if args.debug:
        overrides["debug"] = True
    
    # Store training dataset in overrides
    if args.training_dataset:
        overrides["training_dataset"] = args.training_dataset

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
            from core.learning.micro_trainer import MicroTrainer
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

    sys.exit(main())
