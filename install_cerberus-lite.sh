#!/usr/bin/env bash

set -e

ENV_NAME=cerberus-lite
echo "Creating conda environment: "$ENV_NAME

# initialize conda environment in bash script
eval "$(conda shell.bash hook)"

# create the Cerberus environment in conda
mamba create -y -n $ENV_NAME -c conda-forge -c bioconda \
	python'>=3.8' setuptools"<70.0.0" grpcio=1.43 pyhmmer flash2 \
	ray-default"<=2.6.3" ray-core"<=2.6.3" ray-tune"<=2.6.3" ray-dashboard"<=2.6.3" \
	pyrodigal pyrodigal-gv \
	metaomestats plotly scikit-learn dominate python-kaleido configargparse psutil

conda activate $ENV_NAME

pip install .

cerberus.py --setup

echo "Created conda environment: "$ENV_NAME
echo "To activate run 'conda activate $ENV_NAME'"
echo "Run cerberus.py --download to download databases"
