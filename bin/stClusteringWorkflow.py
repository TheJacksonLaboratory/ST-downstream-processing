#!/opt/conda/bin/python

# Load packages 
import sys
import os
import argparse
import scanpy as sc
import numpy as np
import pandas as pd
import scanorama
from sklearn.manifold import TSNE
from umap import UMAP
from matplotlib import pyplot as plt
from matplotlib import cm
from sklearn.metrics.pairwise import cosine_similarity
from scipy.spatial.distance import cdist
   
def label_transfer(dist, labels):
    class_prob = pd.get_dummies(labels).to_numpy().T @ dist
    class_prob /= np.linalg.norm(class_prob, 2, axis=0)
    return (class_prob.T - class_prob.min(1)) / np.ptp(class_prob, axis=1)
    
def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('True', 'yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('False', 'no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


# Parse command-line arguments
parser = argparse.ArgumentParser(description='Preprocess single cell transcriptomics data.')

parser.add_argument('--filePath', metavar='path', type=str, default=None, help='Path to data.')

parser.add_argument('--useSCdata', type=str2bool, default=True, help='Whether scRNA-seq data is available.')

parser.add_argument('--fileNameST', metavar='name', type=str, default='st_adata_norm.h5ad', help='')
parser.add_argument('--fileNameSC', metavar='name', type=str, default='sc_adata_norm.h5ad', help='')
parser.add_argument('--STdeconvolveSCclusterIds', metavar='name', type=str, default='STdeconvolve_sc_cluster_ids.csv', help='')
parser.add_argument('--STdeconvolvePropNormName', metavar='name', type=str, default='STdeconvolve_prop_norm.csv', help='')
parser.add_argument('--STdeconvolveBetaNormName', metavar='name', type=str, default='STdeconvolve_beta_norm.csv', help='')
parser.add_argument('--STdeconvolveSCloadings', metavar='name', type=str, default='STdeconvolve_sc_pca_feature_loadings.csv', help='')
parser.add_argument('--STdeconvolveSCclusterMarkers', metavar='name', type=str, default='STdeconvolve_sc_cluster_markers.csv', help='')
parser.add_argument('--SPOTlightPropNorm', metavar='name', type=str, default='SPOTlight_prop_norm.csv', help='')

parser.add_argument('--BayesSpaceClusters', metavar='name', type=str, default='bayes_spot_cluster.csv', help='')

parser.add_argument('--nPCs', metavar='PC', type=int, default=30, help='Number of principal components.')
parser.add_argument('--resolution', metavar='name', type=float, default=0.4, help='')

parser.add_argument('--scanpy_UMAP_st_sc', metavar='name', type=str, default='scanpy_UMAP_st_sc.png', help='')
parser.add_argument('--scanpy_UMAP_st_sc_BBKNN', metavar='name', type=str, default='scanpy_UMAP_st_sc_BBKNN.png', help='')
parser.add_argument('--scanorama_UMAP_st_sc', metavar='name', type=str, default='scanorama_UMAP_st_sc.png', help='')

parser.add_argument('--LT_individual_histograms', metavar='name', type=str, default='LT_individual_histograms.png', help='')
parser.add_argument('--LT_individual_histograms_combined', metavar='name', type=str, default='LT_individual_histograms_combined.png', help='')

parser.add_argument('--Topics_LDA_spatial', metavar='name', type=str, default='Topics_LDA_spatial.png', help='')
parser.add_argument('--Topics_NMF_spatial', metavar='name', type=str, default='Topics_NMF_spatial.png', help='')
parser.add_argument('--Topics_LT_PC_spatial', metavar='name', type=str, default='Topics_LT_PC_spatial.png', help='')

parser.add_argument('--UMAP_st_spots_clusters', metavar='name', type=str, default='UMAP_st_spots_clusters.png', help='')
parser.add_argument('--UMAP_clusters_embedding_density', metavar='name', type=str, default='UMAP_clusters_embedding_density.png', help='')
parser.add_argument('--UMAP_LDA_topics', metavar='name', type=str, default='UMAP_LDA_topics.png', help='')
parser.add_argument('--UMAP_NMF_topics', metavar='name', type=str, default='UMAP_NMF_topics.png', help='')
parser.add_argument('--UMAP_LT_PC_topics', metavar='name', type=str, default='UMAP_LT_PC_topics.png', help='')

parser.add_argument('--Clusters_scanpy_spatial', metavar='name', type=str, default='Clusters_scanpy_spatial.png', help='')

parser.add_argument('--violin_topics_LDA', metavar='name', type=str, default='violin_topics_LDA.png', help='')
parser.add_argument('--violin_topics_NMF', metavar='name', type=str, default='violin_topics_NMF.png', help='')
parser.add_argument('--violin_topics_LT_PC', metavar='name', type=str, default='violin_topics_LT_PC.png', help='')

parser.add_argument('--saveFileST', metavar='savefile', type=str, default='st_adata_processed.h5ad', help='Path to a file to save h5ad data into.')
parser.add_argument('--saveFileSC', metavar='savefile', type=str, default='sc_adata_processed.h5ad', help='Path to a file to save h5ad data into.')

args = parser.parse_args()


# Main script
# See more settings at:
# https://scanpy.readthedocs.io/en/stable/generated/scanpy._settings.ScanpyConfig.html
sc.settings.figdir = args.filePath
sc.set_figure_params(dpi_save=300, facecolor='white')

for dirName in ['show/', 'umap/', 'umap_density_clusters_/', 'umap_density_sclusters_/', 'violin/', 'heatmap/']:
    if not os.path.exists(args.filePath + dirName):
        os.makedirs(args.filePath + dirName)

#### Label transfer
#1. To topics from single cells
#2. To spots from single cells
#3. Compare spots transfer to deconvolution results

#Task: Determine cluster composition of LDA topics <br>
#Challenge: topics are intertwined -> hard to match the clusters <br>

#Task: direct label transfer from SC clusters to ST spots <br>
#Prerequisite: Do integration via Scanorama or BBKNN <br>
#Post-task: compare deconvolution results to STdeconvolve proportions (correlate proportions) <br>

# Read pre-processed data
st_adata = sc.read(args.filePath + args.fileNameST)
df_st = pd.DataFrame(index=st_adata.var.index, data=st_adata.X.T.todense(), columns=st_adata.obs.index)
print(df_st.shape)

if args.useSCdata:
    sc_adata = sc.read(args.filePath + args.fileNameSC)
    df_sc = pd.DataFrame(index=sc_adata.var.index, data=sc_adata.X.T.todense(), columns=sc_adata.obs.index)
    ind = df_sc.index.intersection(df_st.index)
    df_st = df_st.loc[ind]
    df_sc = df_sc.loc[ind]
    print(df_st.shape, df_sc.shape)

# Read STdeconvolve results
df_theta = pd.read_csv(args.filePath + args.STdeconvolvePropNormName, index_col=0)
df_beta = pd.read_csv(args.filePath + args.STdeconvolveBetaNormName, index_col=0)

if args.useSCdata:
    se_clusters_SC = pd.read_csv(args.filePath + args.STdeconvolveSCclusterIds, index_col=0).rename({'x': 'cluster_id'}, axis=1)['cluster_id']
    hvg_SC = pd.read_csv(args.filePath + args.STdeconvolveSCloadings, index_col=0).index
    df_markers_SC = pd.read_csv(args.filePath + args.STdeconvolveSCclusterMarkers, index_col=0)

if args.useSCdata:
    # Simple comparison of clusters to topics
    df_beta_st = df_beta.loc[df_beta.index.intersection(df_st.index)]
    df_beta_st.columns = 'X ' + df_beta_st.columns.astype(str)
    df_sc_cl = df_sc.copy().loc[df_beta.index.intersection(df_st.index)]
    df_sc_cl.columns = pd.MultiIndex.from_arrays(se_clusters_SC.reset_index().values.T, names=['cell', 'cluster'])
    df_sc_cl = df_sc_cl.groupby(level='cluster', axis=1).mean()
    df_sc_cl.columns = 'Cluster ' + df_sc_cl.columns.astype(str)
    # Similar approach to label transfer
    df = df_sc_cl.T @ df_beta_st / df_sc_cl.shape[0]
    df /= np.linalg.norm(df, 2, axis=0)
    df = (df.T - df.min(1)) / df.values.ptp(1)
    df.T.round(3) #.style.background_gradient(axis=None)

# Integrating with BBKNN
# This is only to see the UMAP of SC and ST together
# Not using it with label transfer
if args.useSCdata: 
    st_adata = sc.read(args.filePath + args.fileNameST)
    sc_adata = sc.read(args.filePath + args.fileNameSC)
    adata_all = st_adata.concatenate(sc_adata, batch_categories=['st', 'sc'])
    sc.pp.highly_variable_genes(adata_all, flavor="seurat", n_top_genes=2000)
    sc.pp.pca(adata_all, use_highly_variable=True)
    sc.pp.neighbors(adata_all)
    sc.tl.umap(adata_all)
    sc.pl.umap(adata_all, color=['batch'], palette=sc.pl.palettes.vega_20_scanpy, save='/' + args.scanpy_UMAP_st_sc)
    df_before = pd.DataFrame(adata_all.obsp['connectivities'].todense(), index=adata_all.obs.batch, columns=adata_all.obs.batch).xs('st', axis=0).xs('sc', axis=1)
    sc.external.pp.bbknn(adata_all, batch_key='batch')
    sc.tl.umap(adata_all)
    sc.pl.umap(adata_all, color=['batch'], palette=sc.pl.palettes.vega_20_scanpy, save='/' + args.scanpy_UMAP_st_sc_BBKNN)
    df_after = pd.DataFrame(adata_all.obsp['connectivities'].todense(), index=adata_all.obs.batch, columns=adata_all.obs.batch).xs('st', axis=0).xs('sc', axis=1)

# Correlation similarity of gene expression in PC space
# Integrating with Scanorama
if args.useSCdata:
    integrated = scanorama.integrate([df_st.values.T, df_sc.values.T], [df_st.index.values, df_sc.index.values])[0]
    umap_st = UMAP(random_state=2).fit_transform(integrated[0]).T
    umap_sc = UMAP(random_state=2).fit_transform(integrated[1]).T
    fig, ax = plt.subplots(1, 1, figsize=(6, 6))
    ax.scatter(umap_st[0], umap_st[1], alpha=0.95, s=2, label='st')
    ax.scatter(umap_sc[0], umap_sc[1], alpha=0.95, s=2, label='sc')
    plt.legend()
    fig.savefig(args.filePath + '/' + args.scanorama_UMAP_st_sc, facecolor='white', dpi=300);
    plt.close(fig)

    df_similarity = pd.DataFrame(data=1 - cdist(integrated[0], integrated[1], metric='correlation').T).fillna(0)
    v_in_pc = label_transfer(df_similarity.values, se_clusters_SC.values)
    
    # Plot individual histograms
    if True:
        fig, ax = plt.subplots(1, 1, figsize=(10, 10))
        pd.DataFrame(v_in_pc).hist(bins=50, ax=ax);
        fig.savefig(args.filePath + '/' + args.LT_individual_histograms, facecolor='white', dpi=300);
        plt.close(fig)
    
    # Plot combined histogram
    if True:
        fig, ax = plt.subplots(1, 1, figsize=(5, 5))
        for i in range(v_in_pc.shape[1]):
            pd.DataFrame(v_in_pc)[i].hist(bins=100, alpha=0.5, ax=ax)
        fig.savefig(args.filePath + '/' + args.LT_individual_histograms_combined, facecolor='white', dpi=300);
        plt.close(fig)
    
    # Add LT results to adata 
    dfb = pd.DataFrame(v_in_pc)
    dfb.columns = 'LT PC ' + dfb.columns.astype(str)
    dfb.index = st_adata.obs.index.values
    for col in dfb.columns:
        st_adata.obs[col] = dfb[col]
    
    #dfc = pd.DataFrame(v_in_bbknn)
    #dfc.columns = 'LT BBKNN ' + dfc.columns.astype(str)
    #dfc.index = st_adata.obs.index.values
    #for col in dfc.columns:
    #    st_adata.obs[col] = dfc[col]

# Add LDA proportions to adata
df_theta = pd.read_csv(args.filePath + args.STdeconvolvePropNormName, index_col=0)
df_theta.columns = 'Topic LDA ' + df_theta.columns.astype(str)
for col in df_theta.columns:
    st_adata.obs[col] = df_theta[col]   

# Add NMF proportions to adata
if args.useSCdata:
  df_theta = pd.read_csv(args.filePath + args.SPOTlightPropNorm, index_col=0).set_index('barcodes').drop('res_ss', axis=1)
  df_theta.columns = 'Topic NMF ' + df_theta.columns.astype(str)
  for col in df_theta.columns:
      st_adata.obs[col] = df_theta[col]

# Make plots with proportions
# These plots have a uniform color-mapping of scanpy
if True:
    plt.rcParams["figure.figsize"] = (5, 5)
    keys = st_adata.obs.columns[st_adata.obs.columns.str.contains('Topic LDA ')]
    sc.pl.spatial(st_adata, img_key="hires", color=keys, ncols=10, save='/' + args.Topics_LDA_spatial)
    
if args.useSCdata:
    keys = st_adata.obs.columns[st_adata.obs.columns.str.contains('Topic NMF ')]
    sc.pl.spatial(st_adata, img_key="hires", color=keys, ncols=10, save='/' + args.Topics_NMF_spatial)
    
if args.useSCdata:
    keys = st_adata.obs.columns[st_adata.obs.columns.str.contains('LT PC ')]
    sc.pl.spatial(st_adata, img_key="hires", color=keys, ncols=10, save='/' + args.Topics_LT_PC_spatial)
    
    #keys = st_adata.var.index.intersection(all_markers).values
    #sc.pl.spatial(st_adata, img_key="hires", color=keys, ncols=9, save='/' + args.All_Markers_spatial)


# Clsutering and Selection

# SCtransform PCA on vst scale.data
if False:
    df_temp = pd.read_csv(args.filePath + 'scale.data.' + 'st_adata_sctransformed.csv.gz', index_col=0)
    se_var_features = pd.read_csv(args.filePath + 'var.features.' + 'st_adata_sctransformed.csv.gz', index_col=0)['x']

    adata_temp = sc.AnnData(df_temp.T, var=pd.DataFrame(index=df_temp.index))
    adata_temp.var['highly_variable'] = adata_temp.var.index.isin(se_var_features.values)
    
    sc.pp.pca(adata_temp, n_comps=args.nPCs, zero_center=False, use_highly_variable=True)

    st_adata.uns['pca'] = adata_temp.uns['pca']
    st_adata.obsm['X_pca'] = pd.DataFrame(adata_temp.obsm['X_pca'], index=adata_temp.obs.index).reindex(st_adata.obs.index).fillna(0.).values
    st_adata.varm['PCs'] = pd.DataFrame(adata_temp.varm['PCs'], index=adata_temp.var.index).reindex(st_adata.var.index).fillna(0.).values
    st_adata.var['highly_variable'] = adata_temp.var['highly_variable'].reindex(st_adata.var.index).fillna(False)

    del df_temp
    del adata_temp
else:
    sc.pp.pca(st_adata, n_comps=args.nPCs, zero_center=True, use_highly_variable=True)

sc.pp.neighbors(st_adata)
sc.tl.umap(st_adata)
sc.tl.leiden(st_adata, key_added="clusters", resolution=args.resolution)


def getConsensus(ad, n=10, sample_size=0.75, resolution=0.8, n_top_genes=2000, nPC=30):
    def getClusters(ad_in, i, sample_size=sample_size, resolution=resolution, n_top_genes=n_top_genes, nPC=nPC):
        print('Clustering...', i)
        np.random.seed()
        ad_temp = ad_in[np.random.choice(np.arange(ad_in.shape[0]), int(sample_size*ad_in.shape[0]), replace=False), :].copy()
        sc.pp.highly_variable_genes(ad_temp, flavor='seurat', n_top_genes=n_top_genes)
        sc.pp.pca(ad_temp, n_comps=nPC, zero_center=True, use_highly_variable=True)
        sc.tl.umap(ad_temp)
        sc.pp.neighbors(ad_temp)
        sc.tl.leiden(ad_temp, key_added='clusters', resolution=resolution)
        return ad_temp.obs['clusters'].astype(str).reindex(ad_in.obs.index).fillna(-1).astype('category').copy()
    df = pd.concat([getClusters(ad, 'all', sample_size=1)] + [getClusters(ad, i) for i in range(n)], axis=1)
    return df.replace(-1, np.nan).apply(lambda s: s.dropna().value_counts().index[0], axis=1)
    
st_adata.obs['clusters_consensus'] = getConsensus(st_adata, n=50, sample_size=0.75, nPC=args.nPCs, resolution=args.resolution).copy()

BayesSpaceClusters = pd.read_csv(args.filePath + args.BayesSpaceClusters, index_col=0)['spatial.cluster']
st_adata.obs['sclusters'] = (BayesSpaceClusters.reindex(st_adata.obs.index)-1).astype(str).astype('category')

st_adata.obs.to_csv(args.filePath + 'st_adata.obs.temp.csv')

# Make plots of UMAP of ST spots clusters
plt.rcParams["figure.figsize"] = (4, 4)
sc.pl.umap(st_adata, color=["clusters", "sclusters", "total_counts", "n_genes_by_counts"], wspace=0.4, save='/' + args.UMAP_st_spots_clusters)

identity = "clusters"

sc.tl.embedding_density(st_adata, basis='umap', groupby=identity)
sc.pl.embedding_density(st_adata, groupby=identity, ncols=10, save='/' + args.UMAP_clusters_embedding_density)

sc.tl.rank_genes_groups(st_adata, identity, method='wilcoxon', key_added="wilcoxon")
sc.pl.rank_genes_groups_heatmap(st_adata, n_genes=10, key="wilcoxon", groupby=identity, show_gene_labels=True, save='/' + 'DEG_heatmap.png')

# Plot LDA cell topics proportions in UMAP
if True:
    plt.rcParams["figure.figsize"] = (4, 4)
    keys = st_adata.obs.columns[st_adata.obs.columns.str.contains('Topic LDA ')]
    sc.pl.umap(st_adata, color=keys, wspace=0.4, ncols=5, save='/' + args.UMAP_LDA_topics)
    
if args.useSCdata:
    keys = st_adata.obs.columns[st_adata.obs.columns.str.contains('Topic NMF ')]
    sc.pl.umap(st_adata, color=keys, wspace=0.4, ncols=5, save='/' + args.UMAP_NMF_topics)
    
if args.useSCdata:
    keys = st_adata.obs.columns[st_adata.obs.columns.str.contains('LT PC ')]
    sc.pl.umap(st_adata, color=keys, wspace=0.4, ncols=5, save='/' + args.UMAP_LT_PC_topics)

# Make plots of spatial ST spots clusters
if True:
    plt.rcParams["figure.figsize"] = (10, 10)
    sc.pl.spatial(st_adata, img_key="hires", color=[identity], save='/' + args.Clusters_scanpy_spatial) # groups=['1', '2', '3']

# Make violin plots of topic proportions of ST spots by clusters
if True:
    plt.rcParams["figure.figsize"] = (3.5, 3.5)
    keys = st_adata.obs.columns[st_adata.obs.columns.str.contains('Topic LDA ')]
    sc.pl.violin(st_adata, keys, jitter=0.4, groupby=identity, rotation=0, save='/' + args.violin_topics_LDA)
    
if args.useSCdata:
    keys = st_adata.obs.columns[st_adata.obs.columns.str.contains('Topic NMF ')]
    sc.pl.violin(st_adata, keys, jitter=0.4, groupby=identity, rotation=0, save='/' + args.violin_topics_NMF)
    
if args.useSCdata:
    keys = st_adata.obs.columns[st_adata.obs.columns.str.contains('LT PC ')]
    sc.pl.violin(st_adata, keys, jitter=0.4, groupby=identity, rotation=0, save='/' + args.violin_topics_LT_PC)

st_adata.write(args.filePath + '/' + args.saveFileST)

if args.useSCdata:
    sc_adata.write(args.filePath + '/' + args.saveFileSC)

exit(0)
