# V2G ABM smoke test — Oxford ARC deployment

This folder contains everything needed to run the V2G agent-based model on Oxford ARC (Advanced Research Computing) as a smoke test, in two modes:

- **Interactive** — Jupyter notebook (`v2g_smoketest.ipynb`) you click through cell-by-cell. This is the "interactive notes mode" David mentioned at Meeting 6.
- **Batch** — SLURM job (`run_smoketest.slurm`) that runs the four headline smoke tests end-to-end and writes the output to a log file. Useful for proving the model deploys correctly without a human at the keyboard.

---

## Quick start

### 1. SSH to ARC

```bash
ssh username@arc-login.arc.ox.ac.uk
```

(Replace `username` with your Oxford ARC account name.)

### 2. Get the repository onto ARC

Option A (you already have it locally):

```bash
# From your laptop
scp -r ~/Documents/GitHub/v2g-abm-model username@arc-login.arc.ox.ac.uk:~/
```

Option B (clone from GitHub):

```bash
# On ARC
git clone https://github.com/uriangel/v2g-abm-model.git ~/v2g-abm-model
```

### 3. Set up the conda environment (one-time)

```bash
cd ~/v2g-abm-model/arc_smoketest
module load Anaconda3
conda env create -f environment.yml
conda activate v2g-abm
```

If `conda env create` is slow on ARC (the conda solver can take 10+ minutes), use `mamba` instead:

```bash
module load Mamba   # if ARC has Mamba; otherwise stick with conda
mamba env create -f environment.yml
```

### 4a. Interactive mode (Jupyter notebook)

ARC provides Jupyter via the OnDemand portal: https://ondemand.arc.ox.ac.uk

- Log in with your Oxford SSO credentials
- Apps → Jupyter Lab → request 1 CPU, 4 GB, 1 hour
- Once started, navigate to `~/v2g-abm-model/arc_smoketest/v2g_smoketest.ipynb`
- Run cells in order

### 4b. Batch mode (SLURM)

```bash
cd ~/v2g-abm-model
sbatch arc_smoketest/run_smoketest.slurm
```

Check job status:

```bash
squeue -u $USER
```

When the job finishes, the output will be in `v2g_smoketest_<job_id>.out` in the submission directory.

---

## What the smoke test proves

If both modes complete without error, the following are confirmed:

1. The Python environment on ARC matches the environment used in development
2. The full V2G model imports correctly (all 9 source files in `src/`)
3. The agent step loop runs (24-hour single-agent trace)
4. The two-country annual sweep runs (6 country/CF combinations, 80 agents each, ~15 seconds)
5. The literature-anchored aging table renders (pure Python arithmetic on Wong 2026 published values)
6. The retail vs wholesale pricing scenarios produce the expected zero-V2G-at-wholesale finding
7. The W10.R economics smoke test produces the expected per-typology profit-and-loss numbers

---

## Expected output (headline)

The two-country fleet sweep should produce something close to:

```
 Country |   CF | V2G EVs | V2G kWh/yr |          Net
--------------------------------------------------------
  Israel |   V0 |       0 |          0 | -176,973 NIS
  Israel |  V1G |       0 |          0 |  -85,870 NIS
  Israel |  V2G |    ~42 |    ~16,000 |  -68,758 NIS (vs V1G: +17k NIS)
      UK |   V0 |       0 |          0 |  -39,479 GBP
      UK |  V1G |       0 |          0 |  -28,299 GBP
      UK |  V2G |    ~42 |    ~17,000 |  -53,588 GBP (vs V1G: -25k GBP)
```

Note the SEM is stochastic — `n_v2g_opted` will vary by ±5 between runs due to the intention sampling.

---

## Files

- `v2g_smoketest.ipynb` — the interactive notebook (5 cells, 5 minutes click-through)
- `environment.yml` — conda environment spec
- `run_smoketest.slurm` — batch submission script
- `README.md` — this file

---

## What this does NOT cover

This smoke test is **not** the sensitivity sweep. It is a "does the model deploy and run" check only.

The full sensitivity sweeps (α × β grid, charger CAPEX 2024 vs 2028, FFR participation rates, driver-share variation) are planned for W12 once the supervisor signs off on the W10 baseline.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'src'`** — make sure you ran the notebook from `arc_smoketest/` (it adds `..` to `sys.path` in cell 2) OR run from the repo root.

**Conda solver hangs** — use mamba (see Quick start) or download a fresh `Miniconda3` installer if ARC's Anaconda module is too old.

**`module load Anaconda3` not found** — list available modules with `module avail`; the exact module name on ARC may have changed.

**Slurm job pending forever** — check `sinfo` for available partitions and adjust `--partition=` in the SLURM script accordingly.
