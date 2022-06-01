#!/opt/conda/bin/python

# Load packages 
import sys
import os
import argparse
import scanpy as sc
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import scipy.stats
from scipy.sparse import csr_matrix


# Parse command-line arguments
parser = argparse.ArgumentParser(description='Preprocess spatial traqnscriptomics data.')

parser.add_argument('--filePath', metavar='path', type=str, default=None, help='Path to data.')
parser.add_argument('--npFactorsOutputName', metavar='filename', type=str, default=None, help='Name of files with counts.')
parser.add_argument('--rawAdata', metavar='h5file', type=str, default=None, help='Name of the h5ad file.')
parser.add_argument('--mitoFile', metavar='file', type=str, default=None, help='Path and name of the mito file.')

parser.add_argument('--pltFigSize', metavar='figsize', type=int, default=6, help='Figure size.')
parser.add_argument('--stQCinName', metavar='name', type=str, default='st_QC_in.png', help='Figure name.')
parser.add_argument('--stQCoutName', metavar='name', type=str, default='st_QC_out.png', help='Figure name.')

parser.add_argument('--stQCviolinName', metavar='name', type=str, default='stQCViolin.png', help='Figure name.')

parser.add_argument('--minCounts', metavar='cutoff', type=int, default=500, help='Min counts per spot.')
parser.add_argument('--minGenes', metavar='cutoff', type=int, default=250, help='Min genes per spot.')
parser.add_argument('--minCells', metavar='cutoff', type=int, default=1, help='Min cells per gene.')

parser.add_argument('--nHVGs', metavar='hvg', type=int, default=2000, help='Number of vighly variable genes.')

parser.add_argument('--histplotQCmaxTotalCounts', metavar='cutoff', type=int, default=10000, help='Max total counts.')
parser.add_argument('--histplotQCminGeneCounts', metavar='cutoff', type=int, default=4000, help='Min gene counts.')
parser.add_argument('--histplotQCbins', metavar='number', type=int, default=40, help='Number of bins.')

parser.add_argument('--histogramPlotAllName', metavar='name', type=str, default='st_histogrtam_all.png', help='Figure name.')
parser.add_argument('--histogramPlotOutName', metavar='name', type=str, default='st_histogrtam_out.png', help='Figure name.')
parser.add_argument('--histWithWithoutNorm', metavar='name', type=str, default='st_histogram_with_without_normalization.png', help='Figure name.')

parser.add_argument('--SCtransform', metavar='name', type=str, default='true', help='Use SCtransform.')

parser.add_argument('--npNormalizedOutputName', metavar='File name', type=str, default='st_adata_sctransformed.csv.gz', help='Name of the normalized counts file.')

parser.add_argument('--nameX', metavar='File name', type=str, default='st_adata_X.csv.gz', help='Name of the counts file.')
parser.add_argument('--nameVar', metavar='File name', type=str, default='st_adata.var.csv', help='Name of the features file.')
parser.add_argument('--nameObs', metavar='File name', type=str, default='st_adata.obs.csv', help='Name of the observations file.')

parser.add_argument('--nameDataPlain', metavar='File name', type=str, default='st_adata_plain.h5ad', help='Name of the data save file.')
parser.add_argument('--nameDataNorm', metavar='File name', type=str, default='st_adata_norm.h5ad', help='Name of the data save file.')

args = parser.parse_args()


# Main script
# See more settings at:
# https://scanpy.readthedocs.io/en/stable/generated/scanpy._settings.ScanpyConfig.html
sc.settings.figdir = args.filePath

if not os.path.exists(args.filePath + 'violin/'):
    os.makedirs(args.filePath + 'violin/')
    
if not os.path.exists(args.filePath + 'show/'):
    os.makedirs(args.filePath + 'show/')

st_adata = sc.read(args.filePath + '/' + args.rawAdata)
print(st_adata.shape)

f_temp = pd.read_csv(args.filePath + '/' + args.npFactorsOutputName, header=0).values.T[0]
st_adata.obs['norm_factors'] = pd.Series(index=st_adata.obs[st_adata.obs['in_tissue']==1].index, data=f_temp).reindex(st_adata.obs.index)

mito = pd.read_csv(args.mitoFile, index_col=['Symbol', 'MCARTA2_LIST'], delimiter='\t')['EnsemblGeneID']
mito = mito.xs(1, level='MCARTA2_LIST').sort_index().reset_index()
print(mito)

st_adata.var["mt"] = st_adata.var_names.isin(mito['Symbol'])
sc.pp.calculate_qc_metrics(st_adata, qc_vars=["mt"], inplace=True)

plt.rcParams["figure.figsize"] = (args.pltFigSize, args.pltFigSize)

st_adata.obs['in_tissue_cat'] = st_adata.obs['in_tissue'].replace({1: 'in', 0:'out'}).astype('category')

sc.pl.violin(st_adata, ["pct_counts_mt", "total_counts", "n_genes_by_counts"], jitter=0.4, groupby='in_tissue_cat', rotation=0, save='/' + args.stQCviolinName)

keys = ["in_tissue", "pct_counts_mt", "total_counts", "n_genes_by_counts"]
st_adata_in = st_adata[st_adata.obs['in_tissue']==1].copy()
sc.pl.spatial(st_adata_in, img_key="hires", color=keys, save='/' + args.stQCinName)

keys = ["pct_counts_mt", "total_counts", "n_genes_by_counts"]
st_adata_out = st_adata[st_adata.obs['in_tissue']!=1].copy()
sc.pp.filter_cells(st_adata_out, min_counts=args.minCounts)
sc.pp.filter_cells(st_adata_out, min_genes=args.minCells)
sc.pp.filter_genes(st_adata_out, min_cells=args.minGenes)
sc.pl.spatial(st_adata_out, img_key="hires", color=keys, save='/' + args.stQCoutName)

def histplotQC(se_data, bins, ax):
    try:
        ax.hist(se_data, density=True, bins=bins, color='navy', alpha=0.3)
        kde = scipy.stats.gaussian_kde(se_data)
        xx = np.linspace(min(se_data), max(se_data), 300)
        ax.set_xlabel(se_data.name)
        ax.set_ylabel('Density')
        ax.plot(xx, kde(xx), color='crimson')
        ax.set_xlim([0, ax.get_xlim()[1]])
    except:
        pass
    return
    
fig, axs = plt.subplots(1, 5, figsize=(args.pltFigSize*5, args.pltFigSize))
histplotQC(st_adata.obs["total_counts"], bins=args.histplotQCbins, ax=axs[0])
histplotQC(st_adata.obs["total_counts"][st_adata.obs["total_counts"] < args.histplotQCmaxTotalCounts], bins=args.histplotQCbins, ax=axs[1])
histplotQC(st_adata.obs["n_genes_by_counts"], bins=args.histplotQCbins, ax=axs[2])
histplotQC(st_adata.obs["n_genes_by_counts"][st_adata.obs["n_genes_by_counts"] < args.histplotQCminGeneCounts], bins=args.histplotQCbins, ax=axs[3])
histplotQC(st_adata.obs["pct_counts_mt"], bins=args.histplotQCbins, ax=axs[4])
fig.tight_layout()
fig.savefig(args.filePath + '/st_histogrtam_all.png', facecolor='white')

fig, axs = plt.subplots(1, 5, figsize=(args.pltFigSize*5, args.pltFigSize))
histplotQC(st_adata[st_adata.obs['in_tissue']==1].obs["total_counts"], bins=args.histplotQCbins, ax=axs[0])
histplotQC(st_adata[st_adata.obs['in_tissue']==1].obs["total_counts"][st_adata[st_adata.obs['in_tissue']==1].obs["total_counts"] < args.histplotQCmaxTotalCounts], bins=args.histplotQCbins, ax=axs[1])
histplotQC(st_adata[st_adata.obs['in_tissue']==1].obs["n_genes_by_counts"], bins=args.histplotQCbins, ax=axs[2])
histplotQC(st_adata[st_adata.obs['in_tissue']==1].obs["n_genes_by_counts"][st_adata[st_adata.obs['in_tissue']==1].obs["n_genes_by_counts"] < args.histplotQCminGeneCounts], bins=args.histplotQCbins, ax=axs[3])
histplotQC(st_adata[st_adata.obs['in_tissue']==1].obs["pct_counts_mt"], bins=args.histplotQCbins, ax=axs[4])
fig.tight_layout()
fig.savefig(args.filePath + '/st_histogrtam_in.png', facecolor='white')
plt.close(fig)

# TO DO: args.histogramPlotOutName

# Remove spots outside tissue
st_adata = st_adata[st_adata.obs['in_tissue']==1]
print('Filtered out spots outside tissue:', st_adata.shape)

st_adata_raw = st_adata.copy()

if args.SCtransform=='true':
    temp_normed = pd.read_csv(args.filePath + '/' + args.npNormalizedOutputName, index_col=0, header=0)
    st_adata = st_adata[temp_normed.columns, temp_normed.index]
    st_adata.X = csr_matrix(temp_normed.T)
else:
    st_adata.X = csr_matrix(st_adata.X / st_adata.obs['norm_factors'].values[:, None])

sc.pp.filter_cells(st_adata, min_counts=args.minCounts)
sc.pp.filter_cells(st_adata, min_genes=args.minGenes)
sc.pp.filter_genes(st_adata, min_cells=args.minCells)
print('Filtered spots and genes:', st_adata.shape)

# Effect of normalization by size factors
if True:
    fig, ax = plt.subplots(figsize=(args.pltFigSize, args.pltFigSize))
    display_cutoff = 10**5
    
    se = pd.Series(np.array(st_adata.X.sum(axis=1)).T[0])
    se = se[se<display_cutoff]
    print('Number of spots displayed:', se.shape)
    se.hist(bins=100, alpha=0.75, ax=ax)
    #ax.set_xlim(0, display_cutoff);
    
    se = pd.Series(np.array(st_adata_raw.X.sum(axis=1)).T[0])
    se = se[se<display_cutoff]
    print('Number of spots displayed:', se.shape)
    se.hist(bins=100, alpha=0.75, ax=ax)
    #ax.set_xlim(0, display_cutoff);
    
    fig.savefig(args.filePath + '/' + args.histWithWithoutNorm, facecolor='white', dpi=300);
    plt.close(fig)
    
if not args.SCtransform=='true':
    sc.pp.log1p(st_adata)
    
sc.pp.highly_variable_genes(st_adata, flavor="seurat", n_top_genes=args.nHVGs)

# Save normalized data to open in R and Python
if True:   
    pd.DataFrame(st_adata.X.T.todense()).to_csv(args.filePath + '/' + args.nameX)
    st_adata.var.to_csv(args.filePath + '/' + args.nameVar)
    st_adata.obs.to_csv(args.filePath + '/' + args.nameObs)   
    st_adata.write(args.filePath + '/' + args.nameDataNorm)

exit(0)