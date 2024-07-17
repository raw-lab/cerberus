# -*- coding: utf-8 -*-
"""cerberus_report.py: Module to create the final HTML reports and tsv files
"""

def warn(*args, **kwargs):
    pass
import warnings
warnings.warn = warn

from collections import OrderedDict
import os
from pathlib import Path
import time
import shutil
import base64
import re
from dominate.util import raw
import pandas as pd
import pkg_resources as pkg
import plotly.express as px
import dominate
from dominate.tags import *


# standard html header to include plotly script
htmlHeader = [
    '<html>',
    '<head><meta charset="utf-8" />',
    '    <script src="plotly-2.0.0.min.js"></script>',
    '</head>',
    '<body>\n']

# TODO: Option for how to include plotly.js.
# False uses script in <head>, 'cdn' loads from internet.
# Can I use both???
PLOTLY_SOURCE = 'cdn'

# Data resources
STYLESHEET = pkg.resource_stream('cerberus_x', 'style.css').read().decode()
ICON = base64.b64encode(pkg.resource_stream('cerberus_x', 'cerberus_logo.jpg').read()).decode()
PLOTLY = pkg.resource_filename('cerberus_x', 'plotly-2.0.0.min.js')


######### Create Report ##########
def createReport(figSunburst, figCharts, config, subdir):
    path = f"{config['DIR_OUT']}/{subdir}"
    os.makedirs(path, exist_ok=True)

    shutil.copy(PLOTLY, path)
    
    # Sunburst HTML files
    for sample,figures in figSunburst.items():
        outpath = os.path.join(path, sample)
        for name,fig in figures.items():
            with open(f"{outpath}/sunburst_{name}.html", 'w') as htmlOut:
                htmlOut.write("\n".join(htmlHeader))
                htmlOut.write(f"<H1>Sunburst summary of {name} Levels</H1>\n")
                htmlFig = fig.to_html(full_html=False, include_plotlyjs=PLOTLY_SOURCE)
                htmlOut.write(htmlFig + '\n')
                htmlOut.write("\n</body>\n</html>\n")

    # Bar Charts
    for sample,figures in figCharts.items():
        outpath = os.path.join(path, sample)
        for name,fig in figures[0].items():
            outfile = os.path.join(outpath, f"barchart_{name}.html")
            write_HTML_files(outfile, fig, sample, name)
        continue

    return None


########## Write Stats ##########
def write_Stats(outpath:os.PathLike, readStats:dict, protStats:dict, NStats:dict, config:dict):
    dictStats = protStats.copy()

    # Merge Stats
    nstatLabels = ['N25', 'N50', 'N75', 'N90']
    trimLabels = ['passed', 'low quality', 'too many Ns', 'too short', 'low complexity', 'adapter trimmed', 'bases: adapters', 'duplication rate %']
    deconLabels = ['contaminants', 'QTrimmed', 'Total Removed', 'Results']
    reNstats = re.compile(r"N25[\w\s:%()]*>= ([0-9]*)[\w\s:%()]*>= ([0-9]*)[\w\s:%()]*>= ([0-9]*)[\w\s:%()]*>= ([0-9]*)")
    reMinMax = re.compile(r"Max.*:.([0-9]*)\nMin.*:.([0-9]*)")
    reGC = re.compile(r"GC count:\s*([0-9]*)[\w\s]*%:\s*([.0-9]*)")
    reTrim = re.compile(r"Filtering result:[\w\s]*: ([0-9]*)[\w\s]*: ([0-9]*)[\w\s]*: ([0-9]*)[\w\s]*: ([0-9]*)[\w\s]*: ([0-9]*)[\w\s]*: ([0-9]*)[\w\s]*: ([0-9]*)[\w\s]*: ([0-9]*)")
    reDecon = re.compile(r"([0-9]*) reads \([0-9%.]*\)[\s]*([0-9]*)[\w\s(0-9-.%)]*:[\s]*([0-9]*) reads \([0-9%.]*\)[\s]*([0-9]*)[\w\s(0-9-.%)]*:[\s]*([0-9]*) reads \([0-9%.]*\)[\s]*([0-9]*)[\w\s(0-9-.%)]*:[\s]*([0-9]*) reads \([0-9%.]*\)[\s]*([0-9]*)")
    for key,value in readStats.items():
        try:
            # GC Count
            gcCount = reGC.search(value, re.MULTILINE)
            if gcCount: dictStats[key]['GC count'] = gcCount.group(1)
            if gcCount: dictStats[key]['GC %'] = gcCount.group(2)
        except: pass
        try:
            # N25-N90
            Nstats = reNstats.search(value, re.MULTILINE)
            if Nstats:
                for i,label in enumerate(nstatLabels, 1):
                    dictStats[key][label] = Nstats.group(i)
        except: pass
        try:
            # Min-Max fasta
            min_max = reMinMax.search(value, re.MULTILINE)
            if min_max: dictStats[key]['Contig Min Length'] = min_max.group(2)
            if min_max: dictStats[key]['Contig Max Length'] = min_max.group(1)
        except: pass
        try:
            # Trimmed stats
            infile = os.path.join(config['DIR_OUT'], config['STEP'][3], key, "stderr.txt")
            trimStats = '\n'.join(open(infile).readlines())
            trim = reTrim.search(trimStats, re.MULTILINE)
            if trim:
                for i,label in enumerate(trimLabels, 1):
                    dictStats[key]['trim: '+label] = trim.group(i)
        except: pass
        # Decon stats
        try:
            infile = os.path.join(config['DIR_OUT'], config['STEP'][4], key, "stderr.txt")
            deconStats = '\n'.join(open(infile).readlines())
            decon = reDecon.search(deconStats, re.MULTILINE)
            if decon:
                for i,label in enumerate(deconLabels, 0):
                    dictStats[key]['decon: reads'+label] = decon.group(i*2+1)
                    dictStats[key]['decon: bases'+label] = decon.group(i*2+2)
        except: pass
        # Write fasta stats to file
        outfile = os.path.join(outpath, key, "fasta_stats.txt")
        os.makedirs(os.path.join(outpath, key), exist_ok=True)
        with open(outfile, 'w') as writer:
            writer.write(value)

    # N-Stats
    for key,value in NStats.items():
        repeats = [y for x in value.values() for y in x]
        if key in dictStats:
            dictStats[key]["Contigs w/ N-repeats:"] = len(value)
            dictStats[key]["N-repeat Count"] = len(repeats)
            dictStats[key]["N-repeat Total Length"] = sum(repeats)
            dictStats[key]["N-repeat Average "] = round(sum(repeats)/len(repeats), 2)


    # Write Combined Stats to File
    outfile = os.path.join(outpath, "combined", "stats.tsv")
    os.makedirs(os.path.join(outpath, "combined"), exist_ok=True)
    dfStats = pd.DataFrame(dictStats)
    dfStats.to_csv(outfile, sep='\t')

    # Statistical plotting (HTML)
    outfile = os.path.join(outpath, "combined", "stats.html")

    tsv_stats = base64.b64encode(dfStats.to_csv(sep='\t').encode('utf-8')).decode('utf-8')
    dfStats = dfStats.apply(pd.to_numeric).T.rename_axis('Sample').reset_index()
    regex = re.compile(r"^([a-zA-Z]*_)")
    prefixes = {regex.search(x).group(1):i for i,x in dfStats['Sample'].items()}.keys()

    figPlots = OrderedDict()
    for prefix in prefixes:
        dfPre = dfStats[dfStats['Sample'].str.startswith(prefix)]
        dfPre['Sample'] = dfPre['Sample'].apply(lambda x: regex.sub('', x))
        # ORF Calling Results
        try:
            df = dfPre[["Sample", 'Protein Count (Total)', 'Protein Count (>Min Score)']]
            df = df.melt(id_vars=['Sample'], var_name='count', value_name='value')
            fig = px.bar(df, x='Sample', y='value',
                color='count', barmode='group',
                labels=dict(count="", value="Count"))
            figPlots[f'ORF Calling Results ({prefix[:-1]})'] = fig
        except: pass
        # Average Protein Length
        try:
            fig = px.bar(dfPre, x='Sample', y='Average Protein Length',
                labels={'Average Protein Length':"Peptide Length"})
            figPlots[f'Average Protein Length ({prefix[:-1]})'] = fig
        except: pass
        # Annotations
        try: #TODO: Add COG, CAZy...
            columns = ['Sample']
            for column in dfPre.columns:
                if re.search(r'[A-Za-z] ID Count', column):
                    columns.append(column)
            df = dfPre[columns]
            columns = {col:col.replace(" Count", "") for col in columns}
            df.rename(columns=columns, inplace=True)
            df = df.melt(id_vars=['Sample'], var_name='group', value_name='value')
            fig = px.bar(df, x='Sample', y='value', color='group', barmode='group',
                labels={'value': 'count', 'group':''})
            figPlots[f'Annotations ({prefix[:-1]})'] = fig
        except: pass
        # GC %
        try:
            df = dfPre[['Sample', 'GC %']]
            fig = px.bar(df, x='Sample', y='GC %',
                labels={'GC %':'GC Percent (%)'}
            )
            figPlots[f'GC (%) ({prefix[:-1]})'] = fig
        except: pass
        # Metaome Stats
        try:
            df = dfPre[['Sample', 'N25', 'N50', 'N75', 'N90']]
            df = df.melt(id_vars=['Sample'], var_name='group', value_name='value')
            fig = px.bar(df, x='Sample', y='value',
                color='group', barmode='group',
                labels=dict(group="", value="Sequence Length")
            )
            figPlots[f'Assembly Stats ({prefix[:-1]})'] = fig
        except: pass
        # Contig Min Max
        try:
            df = dfPre[['Sample', 'Contig Min Length', 'Contig Max Length']]
            df = df.melt(id_vars=['Sample'], var_name='group', value_name='value')
            fig = px.bar(df, x='Sample', y='value', text='value',
                color='group', barmode='group',
                labels=dict(group="", value="Sequence Length")
            )
            fig.update_traces(textposition='outside')
            figPlots[f'Min-Max FASTA Length ({prefix[:-1]})'] = fig
        except: pass

    # Update Graph Colors & Export
    os.makedirs(os.path.join(outpath, "combined", "img"),exist_ok=True)
    for key in figPlots.keys():
        figPlots[key].update_layout(dict(plot_bgcolor='White', paper_bgcolor='White'))
        figPlots[key].update_xaxes(showline=True, linewidth=2, linecolor='black')
        figPlots[key].update_yaxes( showline=True, linewidth=2, linecolor='black',
                                    showgrid=True, gridwidth=1, gridcolor='LightGray')
        figPlots[key].write_image(os.path.join(outpath, "combined", "img", key+'.svg'))

    # Create HTML with Figures
    with dominate.document(title='Stats Report') as doc:
        with doc.head:
            meta(charset="utf-8")
            script(type="text/javascript", src="plotly-2.0.0.min.js")
            with style(type="text/css"):
                raw('\n'+STYLESHEET)
        with div(cls="document", id="metacerberus-summary"):
            with h1(cls="title"):
                img(src=f"data:image/png;base64,{ICON}", height="40")
                a("METACERBERUS", cls="reference external", href="https://github.com/raw-lab/metacerberus")
                raw(" - Statistical Summary")
            with div(cls="contents topic", id="contents"):
                with ul(cls="simple"):
                    li(a("Summary", cls="reference internal", href="#summary"))
                    with ul():
                        for key in figPlots.keys():
                            li(a(f"{key}", cls="reference internal", href=f"#{key}"))
                    li(a("Downloads", cls="reference internal", href="#downloads"))
            with div(h1("Summary"), cls="section", id="summary"):
                for key,fig in figPlots.items():
                    with div(h2(f"{key}"), cls="section", id=f"{key}"):
                        raw(fig.to_html(full_html=False, include_plotlyjs=PLOTLY_SOURCE))
            with div(cls="section", id="downloads"):
                h1("Downloads")
                with div(cls="docutils container", id="attachments"):
                    with blockquote():
                        with div(cls="docutils container", id="table-1"):
                            with dl(cls="docutils"):
                                data_URI = f"data:text/tab-separated-values;base64,{tsv_stats}"
                                dt("Combined Stats:")
                                dd(a("combined_stats.tsv", href=data_URI, download="combined_stats.tsv", draggable="true"))
                div(time.strftime("%Y-%m-%d", time.localtime()), cls="docutils container", id="metadata")

    with open(outfile, 'w') as writer:
        writer.write(doc.render())

    return dfStats


########## Write PCA Report ##########
def write_PCA(outpath, pcaFigures):
    # PCA Files
    os.makedirs(os.path.join(outpath), exist_ok=True)
    for database,figures in pcaFigures.items():
        prefix = f"{outpath}/{database}"
        with open(prefix+"_PCA.html", 'w') as htmlOut:
            htmlOut.write("\n".join(htmlHeader))
            htmlOut.write(f"<h1>PCA Report for {database}<h1>\n")
            for graph,fig in figures.items():
                if type(fig) is pd.DataFrame:
                    fig.to_csv(f"{prefix}_{graph}.tsv", index=False, header=True, sep='\t')
                else:
                    htmlFig = fig.to_html(full_html=False, include_plotlyjs=PLOTLY_SOURCE)
                    htmlOut.write(htmlFig + '\n')
                    fig.write_image(os.path.join(outpath, "img", f"{database}_{graph}.svg"))
            htmlOut.write('\n</body>\n</html>\n')
    return


########## Write Tables ##########
def writeTables(table_path: os.PathLike, filePrefix: os.PathLike):
    if not Path(table_path).exists():
        return
    table = pd.read_csv(table_path, sep='\t')

    regex = re.compile(r"^lvl[0-9]: ")
    table['Name'] = table['Name'].apply(lambda x : regex.sub('',x))
    try:
        levels = int(max(table[table.Level != 'Function'].Level))
        for i in range(1,levels+1):
            filter = table['Level']==str(i)
            table[filter][['Name','Count']].to_csv(f"{filePrefix}_level-{i}.tsv", index = False, header=True, sep='\t')
        regex = re.compile(r"^K[0-9]*: ")
        table['Name'] = table['Name'].apply(lambda x : regex.sub('',x))
    except:
        return
    table[table['Level']=='Function'][['Id','Name','Count']].to_csv(f"{filePrefix}_level-id.tsv", index = False, header=True, sep='\t')
    return


########## Write HTML Files ##########
def write_HTML_files(outfile, figure, sample, name):
    sample = re.sub(r'^[a-zA-Z]*_', '', sample)
    with dominate.document(title=f'MetaCerberus: {name} - {sample}') as doc:
        with doc.head:
            meta(charset="utf-8")
            script(type="text/javascript", src="plotly-2.0.0.min.js")
            with style(type="text/css"):
                raw('\n'+STYLESHEET)
        with div(cls="document", id="metacerberus-report"):
            # Header
            with h1(cls="title"):
                img(src=f"data:image/png;base64,{ICON}", height="40")
                a("METACERBERUS", cls="reference external", href="https://github.com/raw-lab/metacerberus")
                raw(f" - {name} Bar Graphs for '{sample}'")
            # Side Panel
            with div(cls="contents topic", id="contents"):
                with ul(cls="simple"):
                    li("(Bargraphs might take a few minutes to load)", cls="reference internal")
                    li("*Clicking on a bar in the graph displays the next level.")
                    li("The graph will cycle back to the first level after reaching the last level.")
            # Main Content
            with div(h1(f"{name} Levels"), cls="section", id="summary"):
                levels = {}
                for title, figure in figure.items():
                    htmlFig = figure.to_html(full_html=False, include_plotlyjs=PLOTLY_SOURCE)
                    try:
                        id = re.search('<div id="([a-z0-9-]*)"', htmlFig).group(1)
                    except:
                        continue
                    levels[id] = title
                    display = "block" if title=="Level 1" else "none"
                    htmlFig = htmlFig.replace('<div>', f'<div id="{title}" style="display:{display};">', 1)
                    raw(htmlFig)
                div(time.strftime("%Y-%m-%d", time.localtime()), cls="docutils container", id="metadata")
            # Scripts
            with script():
                for id, title in levels.items():
                    level = int(title.split(':')[0][-1])
                    raw(f"""
                document.getElementById("{id}").on('plotly_click', function(data){{
                    var name = data.points[0].x;
                    var id = "Level {level+1}: " + name
                    element = document.getElementById(id)
                    if (element !== null)
                        element.style.display = "block";
                    else
                        document.getElementById("Level 1").style.display = "block";
                    document.getElementById("{title}").style.display = "none";
                    // Refresh size
                    var event = document.createEvent("HTMLEvents");
                    event.initEvent("resize", true, false);
                    document.dispatchEvent(event);
                }});""")
    with open(outfile, 'w') as writer:
        writer.write(doc.render())
    return


# Save Annotated GFF and GenBank files
#TODO: Add embl
def write_datafiles(gff:Path, fasta:Path, amino:Path, summary:Path, out_gff:Path, out_genbank:Path):
    # Create amino acid index
    faa_idx = dict()
    with open(amino) as read_faa:
        line_faa = read_faa.readline()
        while line_faa:
            if line_faa.startswith(">"):
                line = line_faa.strip().split()[0][1:]
                faa_idx[line] = read_faa.tell()
            line_faa = read_faa.readline()

    # Read in GFF data
    gff_data = dict()
    with out_gff.open('w') as writer_gff, out_gff.with_suffix(".gtf").open('w') as writer_gtf:
        print("##gff-version 2", file=writer_gtf)
        with open(gff) as read_gff, summary.open() as read_summary:
            read_summary.readline()
            for line in read_gff:
                if line.startswith('#'):
                    writer_gff.write(line)
                else:
                    data = line.split('\t')[0:8]
                    summ = read_summary.readline().split('\t')
                    attributes = [f"ID={summ[0]}", f"Name={summ[1]}",
                                        f"Alias={summ[2]}", f"Dbxref={summ[3]}", f"evalue={summ[4]}",
                                        f"product_start={summ[10]}", f"product_end={summ[11]}", f"product_length={summ[12]}"]
                    print(*data, ';'.join(attributes), sep='\t', file=writer_gff)
                    print(*data, ';'.join(attributes), sep='\t', file=writer_gtf)
                    if data[0] not in gff_data:
                        gff_data[data[0]] = list()
                    att = dict()
                    for a in attributes:
                        a = a.split('=')
                        att[a[0]] = a[1]
                    gff_data[data[0]] += [data + [att]]

        # Write contigs to end of GFF (ROARY compatible)
        # Create GENBANK template
        print("##FASTA", file=writer_gff)
        with open(fasta) as read_fasta, out_genbank.open('w') as writer_gbk:
            locus = False
            line = read_fasta.readline()
            while line:
                if line.startswith(">"):
                    writer_gff.write(line)
                    locus = line.strip()[1:]
                    # read in sequence in fasta file
                    seq_fna = list()
                    line = read_fasta.readline()
                    while line:
                        if line.startswith(">"):
                            break
                        writer_gff.write(line)
                        seq_fna += [line.strip()]
                        line = read_fasta.readline()
                    seq_fna = "".join(seq_fna)
                    print(f"{'LOCUS':<12}{locus:<12} {len(seq_fna)} bp", file=writer_gbk)
                    print(f"{'DEFINITION':<12}", file=writer_gbk)
                    print(f"{'ACCESSION':<12}", file=writer_gbk)
                    print(f"{'VERSION':<12}", file=writer_gbk)
                    print(f"{'KEYWORDS':<12}", file=writer_gbk)
                    print(f"{'SOURCE':<12}", file=writer_gbk)
                    print(f"{'  ORGANISM':<12}", file=writer_gbk)
                    print(f"{'REFERENCE':<12}1", file=writer_gbk)
                    print(f"{'  AUTHORS':<12}", file=writer_gbk)
                    print(f"{'  TITLE':<12}", file=writer_gbk)
                    print(f"{'  JOURNAL':<12}", file=writer_gbk)
                    print(f"{'  PUBMED':<12}", file=writer_gbk)
                    print(f"{'COMMENT':<12}", file=writer_gbk)
                    print(f"{'FEATURES':<21}Location/Qualifiers", file=writer_gbk)
                    print(f'{"     source":<21}{f"1..{len(seq_fna)}"}', file=writer_gbk)
                    print(f'{"":<21}/organism=""', file=writer_gbk)
                    # get gff data
                    locus = locus.split()[0]
                    if locus in gff_data:
                        for data in gff_data[locus]:
                            attributes = data[-1]
                            start = data[3]
                            end = data[4]
                            if data[6] == '+':
                                print(f'{"     CDS":<21}{f"{start}..{end}"}', file=writer_gbk)
                            else:
                                print(f'{"     CDS":<21}{f"complement ({start}..{end})"}', file=writer_gbk)
                            print(f'{"":<21}/codon_start={int(data[7])+1}', file=writer_gbk)
                            print(f'{"":<21}/product="{attributes["Name"]}"', file=writer_gbk)
                            print(f'{"":<21}/db_xref="{attributes["Dbxref"]}"', file=writer_gbk)
                            # load translation from amino acid sequence file, using previously created index
                            translation = f'/translation="'
                            seq_faa = []
                            if attributes["ID"] in faa_idx:
                                with open(amino) as read_faa:
                                    read_faa.seek(faa_idx[attributes["ID"]])
                                    for line_faa in read_faa:
                                        if line_faa.startswith(">"):
                                            break
                                        seq_faa += [line_faa.strip()]
                                translation += re.sub(r'\*', "", ''.join(seq_faa)) + '"'
                            for i in range(0, len(translation), 48):
                                print(f'{"":<21}{translation[i:i+48]}', file=writer_gbk)
                    print(f'{"ORIGIN":<12}', file=writer_gbk)
                    row = list()
                    start = 1
                    for s in range(0, len(seq_fna), 10):
                        row += [seq_fna[s:s+10]]
                        if len(row) == 6:
                            print(f'{start:>9} {" ".join(row)}', file=writer_gbk)
                            row = list()
                            start += 60
                    print(f'{start:>9} {" ".join(row)}', file=writer_gbk)
                    print("//", file=writer_gbk)
                    continue
                line = read_fasta.readline()

    return
