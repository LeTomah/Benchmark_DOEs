# Benchmark_DOEs
## Work in progress

This repository provides the implementation.

For more detailed information, refer to the paper [here](https://).

## Table of contents
- [Introduction](#introduction)
- [Required Data](#required-data)
- [Usage](#usage)

## Introduction


## Required Data
The required data for running the code is available in the `Data` folder. The data includes:

For using gurobi, please put your WLS Access ID, WLS Secret and License ID in "optimization.py", between the quotation marks for the Access ID and the Secret.
## Usage
### For Desktop
To run the methodology, follow these steps:

1. Clone the repository:
   ```bash
   https://github.com/LeTomah/Benchmark_DOEs.git

2. Select your test case and the nodes you want for your graph.

3. Set your Gurobi credentials as environment variables before running
   the optimisation:

   ```bash
   export GUROBI_WLSACCESSID="your-access-id"
   export GUROBI_WLSSECRET="your-secret"
   export GUROBI_LICENSEID="your-license-id"
   ```

4. Launch the code.
   ```bash
   python init.py
   ```

### Surcoût relatif DOE vs OPF

The relative curtailment overcost for a DOE configuration of weight ``alpha``
compared to the OPF baseline is defined as

\[\text{surcoût\_relatif\_DOE}(\alpha) = 100 \times \frac{O_{\text{DOE}}(\alpha) - O_{\text{OPF}}}{O_{\text{OPF}}}\]

where ``O`` denotes the unweighted curtailment component of the objective.
To compute and plot this metric for several ``alpha`` values:

```bash
python init.py --plot-rel-overcost --alpha-list 0,0.5,1.0
```

The command produces `results/rel_overcost_vs_alpha.csv` and the plot
`figures/rel_overcost_vs_alpha.png` (and `.pdf`).

### For Colab
To run the methodology, follow these steps:

***

For any questions or issues, please contact thomas.richard@etu.minesparis.psl.eu
