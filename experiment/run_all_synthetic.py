#!/usr/bin/env python3
"""
Quick script to run all synthetic agent experiments
"""
import subprocess
import sys

def main():
    """Run all synthetic agent experiments"""
    print("Starting synthetic agent experiments...")
    print("This will run conversations for all synthetic agents on all topics.")
    print("="*60)
    
    # Run the synthetic experiments
    cmd = [
        sys.executable,
        "run_synthetic_experiments.py",
        "--max-qa", "15"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("\nAll experiments completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\nError running experiments: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nExperiments interrupted by user")
        sys.exit(1)

if __name__ == "__main__":
    main()
