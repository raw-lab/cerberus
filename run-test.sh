#!/bin/bash

pip install ~/raw-lab/Cerberus >/dev/null

DBPATH=~/database/db-metacerberus

#cerberus.py -h

#cerberus.py --setup -h
#cerberus.py --db-path $DBPATH --download CAZy COG flop
#cerberus.py --setup --db-path $DBPATH
#cerberus.py --update --db-path $DBPATH

#cerberus.py --list-db --db-path $DBPATH

#cerberus.py --download COG CAZy --db-path $DBPATH
#cerberus.py --download --db-path $DBPATH

rm -r temp-results
command time cerberus.py --prodigal data/five_genomes/RW1.fna --hmm COG --keep --dir-out temp-results --db-path $DBPATH --slurm-single

rm -r temp-NfixDB
command time cerberus.py --prodigal data/rhizobium_test/ --hmm temp-db/NFixDB.hmm.gz --dir-out temp-NfixDB --db-path $DBPATH --slurm-single

#rm -r temp-rhizobium
#command time cerberus.py --phanotate data/rhizobium_test/ --hmm COG --dir-out temp-rhizobium --slurm-single --class data/rhizobium_test/samples.tsv --db-path $DBPATH --slurm-single

#rm -r temp-GV
#command time cerberus.py --pyrodigalgv data/giantvirus.fna --hmm VOG --dir-out temp-GV --chunk 1 --db-path $DBPATH --slurm-single

rm -r temp-paired
command time cerberus.py --fraggenescan ~/temp/raw-reads --illumina --hmm COG --dir-out temp-paired --db-path $DBPATH --slurm-single
