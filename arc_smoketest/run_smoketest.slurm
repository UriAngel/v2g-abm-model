#!/bin/bash
#SBATCH --job-name=v2g_smoketest
#SBATCH --partition=short
#SBATCH --time=00:10:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --output=v2g_smoketest_%j.out
#SBATCH --error=v2g_smoketest_%j.err

# Oxford ARC SLURM submission for V2G ABM smoke test
# Submit from the repository root with:  sbatch arc_smoketest/run_smoketest.slurm

set -euo pipefail

echo "=== V2G smoke test on ARC ==="
echo "Job ID:       $SLURM_JOB_ID"
echo "Node:         $SLURMD_NODENAME"
echo "Date:         $(date -Iseconds)"
echo "Working dir:  $(pwd)"
echo

module purge
module load Anaconda3/2024.06-1   # adjust to whatever ARC has installed

source activate v2g-abm || conda activate v2g-abm

echo "Python: $(which python)"
python -V
echo

cd "$SLURM_SUBMIT_DIR"

# Run the headline smoke tests one after the other
python -m src.aging_table_lit
echo
python -m src.smoke_w10b_scenarios
echo
python -m src.smoke_w10d_twocountry
echo
python -m src.smoke_w10r_economics
echo

echo "=== Smoke test complete ==="
