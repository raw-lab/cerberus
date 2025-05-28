# -*- coding: utf-8 -*-

"""cerberus_setup.py: Module for seting up dependencies
"""

import os
import time
import shutil
import subprocess
import platform
import urllib.request as url
import importlib_resources as pkg
from pathlib import Path
import hashlib


PATHFGS = pkg.files("cerberus_x") / 'FGS'


def get_hash(filepath):
    with open(filepath, "rb") as reader:
        md5 = hashlib.md5()
        for chunk in iter(lambda: reader.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()


def list_db(pathDB):
    pathDB = Path(pathDB).absolute()
    pathDB.mkdir(exist_ok=True, parents=True)
    db_tsv = Path(pathDB, "databases.tsv")
    #try:
    #    url.urlretrieve("https://raw.githubusercontent.com/raw-lab/MetaCerberus/main/lib/DB/databases.tsv", db_tsv)
    #except:
    #    print("WARNING: Failed to download database list")
    #    if db_tsv.exists():
    #        print("Using previously downloaded list")
    #    else:
    #        return dict(), dict(), dict(), dict()
    databases = dict()
    url_paths = dict()
    hmm_version = dict()
    hmm_hash = dict()
    downloaded = dict()
    incomplete = dict()
    to_download = dict()
    with db_tsv.open() as reader:
        header = reader.readline().split()
        for line in reader:
            name,filename,urlpath,hash = line.split()
            if name not in databases:
                databases[name] = list()
            databases[name] += [filename]

            if name not in url_paths:
                url_paths[name] = dict()
            url_paths[name][filename] = urlpath

            hmm_version[name] = hash
            hmm_hash[filename] = hash

    for name,filelist in databases.items():
        down = True
        to_down = False
        for filename in filelist:
            filepath = Path(pathDB, filename)
            if not filepath.exists():
                down = False
            elif get_hash(filepath) != hmm_hash[filename]:
                    print("WARNING:", filename, "File hash did not match latest version, either file is corrupt or out of date. Marking as not downloaded.")
                    to_down = True

        if down:
            downloaded[name] = list()
            for filename in filelist:
                filepath = Path(pathDB, filename)
                downloaded[name] += [filepath]
        else:
            to_download[name] = filelist
        if to_down:
            to_download[name] = filelist
    return downloaded, to_download, url_paths, hmm_version


# Downloader
def download_hmm(pathDB, url_list):
    start = time.time()
    def progress(block, read, size):
        nonlocal start
        down = (100*block*read) / size
        if time.time() - start > 10:
            start = time.time()
            print(f"Progress: {round(down,2)}%")
        return

    for filename,urlpath in url_list.items():
        filepath = Path(pathDB, filename)
        print("Downloading:", filename)
        try:
            url.urlretrieve(urlpath, filepath, reporthook=progress)
        except:
            print("Failed to download:", filename)
        else:
            print(f"Progress: 100%")

    return


# Download Database
def download(pathDB, hmms):
    pathDB = Path(pathDB).absolute()
    pathDB.mkdir(exist_ok=True, parents=True)
    print(f"Downloading Database files to {pathDB}")
    
    downloaded,to_download,urls,hmm_version = list_db(pathDB)

    if not hmms:
        if to_download:
            print("This may take a few minutes...")
        else:
            print("\nAll know databases already downloaded")
        for name,filelist in to_download.items():
            download_hmm(pathDB, urls[name])
    
    else:
        print("This may take a few minutes...")
        for hmm in hmms:
            if hmm in downloaded:
                print("Database exists, use --update to re-download:", hmm)
            elif hmm in to_download:
                download_hmm(pathDB, urls[hmm])
            else:
                print("Warning: '",hmm, "' not found in HMMs to download.")
    return


# Update already downloaded databases
def update(pathDB, db_list):
    downloaded,to_download,urls,hmm_md5 = list_db(pathDB)

    # update download list
    to_download = {k:v for k,v in downloaded.items() if k in to_download}
    if db_list:
        to_download = {k:v for k,v in to_download.items() if k in db_list}

    if not to_download:
        print("Requested HMM databases are already up to date")

    for name,filelist in to_download.items():
        print("DB_NAME:", name, filelist)
        for filepath in filelist:
            Path(filepath).unlink()
        download_hmm(pathDB, urls[name])
    return


# Copy FragGeneScanRS
def FGS(pathFGS:os.PathLike = PATHFGS):
    system = platform.system()

    if system == "Windows":
        print("Windows is not supported")
        return None
    subprocess.run(['tar', '-xzf', f'FragGeneScanRS-{system}.tar.gz'], cwd=PATHFGS)

    return os.path.join(PATHFGS, 'FragGeneScanRs')


# Remove Database and FGSRS
def remove(pathDB, pathFGS):
    shutil.rmtree(pathDB, ignore_errors=True)
    shutil.rmtree(os.path.join(pathFGS, "FragGeneScanRS"), ignore_errors=True)
    return
