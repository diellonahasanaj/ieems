import os

def get_next_run_id():
    base_path = "run_storage"

    runs = [d for d in os.listdir(base_path) if d.startswith("run_")]

    if not runs:
        return "run_001"

    numbers = [int(run.split("_")[1]) for run in runs]

    next_number = max(numbers) + 1

    return f"run_{next_number:03d}"