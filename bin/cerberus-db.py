#! /usr/bin/env python


import re
import gzip
import time
import tarfile as tar
import io
import urllib.request as url
import pathlib
import argparse
import json

"""
"""

databases = {
	"AMRFinder": {
		"hmm": "https://ftp.ncbi.nlm.nih.gov/hmm/NCBIfam-AMRFinder/latest/NCBIfam-AMRFinder.HMM.tar.gz",
		"tsv": "https://ftp.ncbi.nlm.nih.gov/hmm/NCBIfam-AMRFinder/latest/NCBIfam-AMRFinder.tsv"
	},
	"CAZy": {
		#"hmm": "https://bcb.unl.edu/dbCAN2/download/Databases/dbCAN_sub.hmm",
		#"hmm": "https://bcb.unl.edu/dbCAN2/download/run_dbCAN_database_total/dbCAN.hmm",
		"hmm": "https://bcb.unl.edu/dbCAN2/download/run_dbCAN_database_total/db_current/dbCAN.hmm",
		"tsv": "https://bcb.unl.edu/dbCAN2/download/run_dbCAN_database_total/db_current/fam-substrate-mapping.tsv"
	},
	"COG": {
		"FAA": "https://ftp.ncbi.nlm.nih.gov/pub/COG/COG2024/data/COGorg24.faa.gz",
		"tsv": ""
	},
	"KOFam": {
		"hmm": "https://www.genome.jp/ftp/db/kofam/profiles.tar.gz",
		"tsv": "https://www.kegg.jp/kegg-bin/download_htext?htext=ko00001&format=json&filedir=",
		#"hmm": pathlib.Path("profiles.tar.gz").absolute().as_uri(),
		#"tsv": pathlib.Path("ko00001.json").absolute().as_uri()
	},
	"MetHMMDB": {
		"hmm": "https://github.com/kciuchcinski/MetHMMDB/archive/master.tar.gz",
	},
	"Pfam": {
		"hmm": "http://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.hmm.gz",
		"tsv": "http://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.clans.tsv.gz"
	}
}

def main():
	for db,files in databases.items():
		print("Downloading", db)
		hmm_data, tsv_data = None, None
		if "hmm" in files:
			print(" HMM:", files["hmm"])
			if files["hmm"].endswith(".tar.gz"):
				hmm_data = download_tar(files["hmm"])
			else:
				hmm_data = download_file(files["hmm"])
		if "tsv" in files:
			print(" TSV:", files["tsv"])
			tsv_data = download_file(files["tsv"])
		func_call = globals()[db]
		func_call(hmm_data, tsv_data)

	return 0


def progress(block, read, size):
	if not hasattr(progress, 'start'):
		progress.start = time.time()
	down = (100*block*read) / size
	if time.time() - progress.start > 10:
		progress.start = time.time()
		print(f"Progress: {round(down,2)}%")
	return


def download_file(file_url):
	url_reader = url.urlopen(file_url)
	if file_url.endswith(".gz"):
		return gzip.decompress(url_reader.read()).decode('utf-8')
	else:
		return url_reader.read().decode('utf-8')
	return None


def download_tar(hmm_url):
	url_reader = url.urlopen(hmm_url)
	hmm_data = list()
	tsv_data = dict()
	with io.BytesIO(url_reader.read()) as tar_bytes:
		with tar.open(fileobj=tar_bytes, mode='r:gz') as reader:
			for file in reader:
				if not file.isfile():
					continue
				if file.name.lower().endswith(".hmm"):
					hmm_data += [reader.extractfile(file.name).read().decode('utf-8')]
				else:
					try:
						tsv_data[file.name] = reader.extractfile(file.name).read().decode('utf-8')
					except:
						pass

	#hmm_data = "".join(hmm_data)
	return {"hmm": hmm_data, "tsv": tsv_data}


#### Recursive Method to load nested json file ####
re_EC = re.compile(r" \[EC:([^;]*)\]")
def convert_json(dicData, writer, level=0, parents={}):
	table = {}
	if level > 0: #first level contains no writable data
		name = dicData['name'].split(maxsplit=1)
		if level < 4:
			parents[level] = name[1]
		else:
			match = re_EC.search(name[1])
			ec = match.group(1) if match else ''
			name[1] = re_EC.sub("", name[1])
			try:
				gene,func = name[1].split('; ')
			except:
				gene = ''
				func = name[1]
			func = func[0].upper() + func[1:]
			if gene == name[0]:
				gene = ''
			print('\t'.join(parents.values()), name[0], func, ec, gene, sep='\t', file=writer)
			table[ name[0] ] = name[1]
	for value in dicData.values():
		if type(value) is list:
			for item in value:
				table.update( convert_json(item, writer, level+1, parents) )
	return table


########## BEGIN INDIVIDUAL PARSING METHODS ##########

def AMRFinder(hmm_data, tsv_data):
	print(f"Processing AMRFinder HMM")
	with io.StringIO(hmm_data["hmm"][0]) as reader, gzip.open(f"AMRFinder.hmm.gz", 'wt') as writer:
		prev = ""
		line = reader.readline()
		while line:
			match = re.search(r'ACC\s+([A-Z0-9.]+)', line)
			if match:
				name = match.group(1)
				print("NAME ", name, file=writer)
			elif prev:
				writer.write(prev)
			prev = line
			line = reader.readline()
		writer.write(prev)

	print(f"Processing AMRFinder TSV")
	with io.StringIO(tsv_data) as reader, open("AMRFinder.tsv", 'w') as writer:
		print("L1", "L2", "ID", "Function", "Gene", sep='\t', file=writer)
		reader.readline()
		for line in reader:
			line = line.rstrip('\n').split('\t')
			ID = line[0]
			GENE = line[3]
			FUNCTION = line[5]
			L1 = line[9]
			L2 = line[10]
			print(L1, L2, ID, FUNCTION, GENE, sep='\t', file=writer)
	return


def CAZy(hmm_data, tsv_data):
	print("WARNING: The CAZy TSV file needs to be updated manually to remove duplicates and fix descriptive names.")

	fun = """AA	Auxiliary activities
CBM	Carb binding modules
CE	Carb esterases
GH	Glycoside hydrolase
GT	Glycosyl trasferase
PL	Polysacharide lyases
"""

	print(f"Processing CAZy HMM")
	#zcat dbCAN-HMMdb-V11.hmm.gz | sed "s/\.hmm//g" | gzip > CAZy.hmm.gz
	with io.StringIO(hmm_data["hmm"][0]) as reader, gzip.open("CAZy.hmm.gz", 'wt') as writer:
		for line in reader:
			if line.startswith("NAME"):
				name = line.rstrip().replace('.hmm','')
				print(name, file=writer)
			else:
				print(line.rstrip(), file=writer)

	#Substrate_high_level	Substrate_curated	Family	Name	EC_Number
	print(f"Processing CAZy TSV")
	with io.StringIO(tsv_data) as reader, open("CAZy.tsv", 'wt') as writer:
		print('L1', 'L2', 'ID', 'Function', 'EC', 'FUN_ID', 'FUN_NAME', sep='\t', file=writer)
		reader.readline() # Skip Header
		for line in reader:
			if line.startswith('#'):
				continue
			#ID,NAME,EC = line.strip('\n').split('\t')
			L1, L2, ID, NAME, EC = line.rstrip('\r\n').split('\t')
			
			match = re.search(r'^([A-Z]+)', ID)
			if match:
				CAT_ID = match.group(1)
				CAT = re.search(rf'{CAT_ID}\t(.+)', fun).group(1)
				print(L1, L2, ID, NAME, EC, CAT_ID, CAT, sep='\t', file=writer)
			else:
				print('ERROR:', line)
	return


def KOFam(hmm_data, tsv_data):
	print(f"Processing KOFam HMM")
	write_all = gzip.open("KOFam_all.hmm.gz", "wt")
	write_prokaryote = gzip.open("KOFam_prokaryote.hmm.gz", "wt")
	write_eukaryote = gzip.open("KOFam_eukaryote.hmm.gz", "wt")
	list_prokaryote = [x.removesuffix(".hmm") for x in hmm_data["tsv"]["profiles/prokaryote.hal"].split()]
	list_eukaryote = [x.removesuffix(".hmm") for x in hmm_data["tsv"]["profiles/eukaryote.hal"].split()]
	for hmm in hmm_data["hmm"]:
		write_all.write(hmm)
		name = re.search(r'NAME\s+([A-Z0-9.]+)', hmm).group(1)
		if name in list_prokaryote:
			write_prokaryote.write(hmm)
		if name in list_eukaryote:
			write_eukaryote.write(hmm)
	write_all.close()
	write_prokaryote.close()
	write_eukaryote.close()
	del hmm_data

	print(f"Processing KOFam TSV")
	json_data = json.loads(tsv_data)
	# parse json
	print("Parsing JSON file")
	with open("KEGG.tsv", 'w') as writer:
		print("L1", "L2", "L3", "ID", "Function", "EC", "Gene", sep='\t', file=writer)
		table = convert_json(json_data, writer)

	return


def MetHMMDB(hmm_data, tsv_data):
	print(f"Processing MetHMMDB HMM")
	with gzip.open(f"MetHMMDB.hmm.gz", 'wt') as writer:
		for hmm in hmm_data["hmm"]:
			print(hmm, file=writer)

	print(f"Processing MetHMMDB TSV")
	with io.StringIO(hmm_data["tsv"]["MetHMMDB-main/DATA/methmm_metadata_v1.0.tsv"]) as reader, open("MetHMMDB.tsv", 'w') as writer:
		print("ID", "Function", sep='\t', file=writer)
		reader.readline() # Skip Header
		for line in reader:
			line = line.rstrip('\n').split('\t')
			ID = line[0]
			FUNCTION = line[4]
			print(ID, FUNCTION, sep='\t', file=writer)

	return


def Pfam(hmm_data, tsv_data):
	print(f"Processing Pfam HMM")
	start = time.time()
	length = len(hmm_data.splitlines())
	counter = 0
	with io.StringIO(hmm_data["hmm"][0]) as reader, gzip.open("Pfam.hmm.gz", 'wt') as writer:
		prev = ""
		line = reader.readline()
		while line:
			counter += 1
			if time.time() - start > 10:
				start = time.time()
				print(f"Progress: {round(100*counter/length,2)}%")

			match = re.search(r'ACC\s+([A-Z0-9]+)', line)
			if match:
				name = match.group(1)
				print("NAME ", name, file=writer)
			elif prev:
				writer.write(prev)
			prev = line
			line = reader.readline()
		writer.write(prev)

	print(f"Processing Pfam TSV")
	with io.StringIO(tsv_data) as reader, open("Pfam.tsv", 'w') as writer:
		print("ID", "Function", "Clan", "Gene", sep='\t', file=writer)
		for line in reader:
			line = line.rstrip('\n').split('\t')
			ID = line[0]
			CLAN = line[1]
			CLAN_NAME = line[2]
			GENE = line[3]
			FUNCTION = line[4]
			print(ID, FUNCTION, CLAN, GENE, sep='\t', file=writer)

	return


if __name__ == "__main__":
	exit(main())
