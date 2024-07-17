# -*- coding: utf-8 -*-

"""cerberus_metastats.py: Module for checking quality of .fastq files
Uses countfasta.py
"""

import os
import subprocess


# Check contigs
def getReadStats(contig, config, subdir):
    path = f"{config['DIR_OUT']}/{subdir}"
    os.makedirs(path, exist_ok=True)
    
    # Metaome_stats
    try:
        command = [ config['EXE_COUNT_ASSEMBLY'], '-f', contig, '-i 100' ]
        with open(f"{path}/stderr.txt", 'w') as ferr, open(f"{path}/read-stats.txt", 'w') as writer:
            proc = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=ferr)
            stats = proc.stdout.decode('utf-8', 'ignore')
            writer.write(stats)
    except Exception as e:
        print(e)
        print("Error: countAssembly.py failed: " + subdir)
        print(command)

    return stats
