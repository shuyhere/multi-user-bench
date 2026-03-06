
import os
import glob
import subprocess
import time
import sys
import argparse

def submit_jobs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=20, help="Number of conversations per seed")
    args = parser.parse_args()

    # Paths
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    seeds_dir = os.path.join(base_dir, "data/seeds")
    logs_dir = os.path.join(base_dir, "logs/slurm_generation")
    
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(os.path.join(base_dir, "data/generated"), exist_ok=True)
    
    # Get all seed files
    seed_files = glob.glob(os.path.join(seeds_dir, "*.json"))
    print(f"Found {len(seed_files)} seed scenarios.")
    
    template = """#!/bin/bash
#SBATCH --job-name=gen_{job_name}
#SBATCH --output={log_path}/%j_{job_name}.log
#SBATCH --error={log_path}/%j_{job_name}.log
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=24:00:00
#SBATCH --partition=main

echo "Starting generation for {seed_file}"
cd {base_dir}

# Use the same python interpreter that submitted the job
{python_path} scripts/generate_dataset.py --seed_file {seed_file} --count {count}

echo "Done"
"""

    count = 0
    for seed_path in seed_files:
        basename = os.path.basename(seed_path)
        job_name = basename.replace(".json", "")
        
        # Write temporary sbatch file
        sbatch_content = template.format(
            job_name=job_name[:15], # Limit name length
            log_path=logs_dir,
            seed_file=seed_path,
            base_dir=base_dir,
            python_path=sys.executable,
            count=args.count
        )
        
        sbatch_filename = os.path.join(logs_dir, f"submit_{job_name}.sbatch")
        with open(sbatch_filename, 'w') as f:
            f.write(sbatch_content)
            
        # Submit
        try:
            cmd = f"sbatch {sbatch_filename}"
            subprocess.run(cmd, shell=True, check=True)
            print(f"Submitted: {job_name}")
            count += 1
            # Rate limit submission slightly to be nice to scheduler
            # time.sleep(0.1) 
        except Exception as e:
            print(f"Failed to submit {job_name}: {e}")
            
    print(f"Submitted {count} jobs.")

if __name__ == "__main__":
    submit_jobs()
