#!/usr/local/bin/Rscript

# Load packages
library(argparse)
library(Matrix)
library(data.table)
library(Seurat)
library(dplyr)
library(gt)
library(SPOTlight)
library(igraph)
library(RColorBrewer)
library(DESeq2)
library(ggplot2)
#library(reticulate)


# Parse command-line arguments
parser <- ArgumentParser()

args <- parser$add_argument_group("Agruments", "required and optional arguments")

args$add_argument("--filePath", help="Path to csv.gz counts file", metavar="dir", required=TRUE)
args$add_argument("--outsPath", help="Path to data", metavar="dir", required=TRUE)

args$add_argument("--nameX", default="st_adata_X.csv.gz", help="Path to X", metavar="file", required=FALSE)
args$add_argument("--nameVar", default="st_adata.var.csv", help="Path to features metadata", metavar="file", required=FALSE)
args$add_argument("--nameObs", default="st_adata.obs.csv", help="Path to observation metadata", metavar="file", required=FALSE)

args$add_argument("--SCnameX", default="sc_adata_X.csv.gz", help="Path to X", metavar="file", required=FALSE)
args$add_argument("--SCnameVar", default="sc_adata.var.csv", help="Path to features metadata", metavar="file", required=FALSE)
args$add_argument("--SCnameObs", default="sc_adata.obs.csv", help="Path to observation metadata", metavar="file", required=FALSE)

args$add_argument("--fileh5", default="raw_feature_bc_matrix.h5", help="File HDF5", metavar="file", required=FALSE) # "filtered_feature_bc_matrix.h5"

args$add_argument("--annoDataDir", default="data/", help="dir", metavar="file", required=FALSE)
args$add_argument("--annoFileCounts", default="counts.csv.gz", help="dir", metavar="file", required=FALSE)
args$add_argument("--annoFileCelltype", default="labels.csv.gz", help="dir", metavar="file", required=FALSE)

args$add_argument("--outsSubDir", default="raw_feature_bc_matrix/", help="dir", metavar="file", required=FALSE)
args$add_argument("--mtxGeneColumn", default=2, type="integer", help="columns index", metavar="col", required=FALSE)
args$add_argument("--countsFactor", default=100, type="integer", help="factor", metavar="factor", required=FALSE)

args$add_argument("--clusterResolution", default=0.3, type="double", help="factor", metavar="factor", required=FALSE)

args$add_argument("--numberHVG", default=3000, type="integer", help="factor", metavar="factor", required=FALSE)
args$add_argument("--numberCellsPerCelltype", default=100, type="integer", help="factor", metavar="factor", required=FALSE)
args$add_argument("--NMFsaveFile", default="SPOTlight_ls_mk_normed_NMF.rds", help="File to save NMF RDS", metavar="file", required=FALSE)

args$add_argument("--SPOTlightScatterpiesName", default="SPOTlight_st_scatterpies.png", help="dir", metavar="file", required=FALSE)
args$add_argument("--SPOTlightScatterpiesSize", default=0.35, type="double", help="dir", metavar="file", required=FALSE)
args$add_argument("--SPOTlightSCclustersName", default="SPOTlight_sc_clusters.png", help="dir", metavar="file", required=FALSE)
args$add_argument("--SPOTlightTopicsName", default="SPOTlight_st_topic_profiles.png", help="dir", metavar="file", required=FALSE)
args$add_argument("--SPOTlightFeaturesName", default="SPOTlight_st_prop.png", help="dir", metavar="file", required=FALSE)
args$add_argument("--imagePath", default="spatial/tissue_lowres_image.png", help="dir", metavar="file", required=FALSE)
args$add_argument("--SPOTlightCorrName", default="SPOTlight_st_prop_corr.png", help="dir", metavar="file", required=FALSE)

args$add_argument("--SPOTlightPropNorm", default="SPOTlight_prop_norm.csv", help="dir", metavar="file", required=FALSE)
args$add_argument("--SPOTlightBetaNorm", default="SPOTlight_beta_norm.csv", help="dir", metavar="file", required=FALSE)
args$add_argument("--SPOTlightSCclusterIds", default="SPOTlight_sc_cluster_ids.csv", help="dir", metavar="file", required=FALSE)
args$add_argument("--SPOTlightSCpca", default="SPOTlight_sc_pca.csv", help="dir", metavar="file", required=FALSE)
args$add_argument("--SPOTlightSCloadings", default="SPOTlight_sc_pca_feature_loadings.csv", help="dir", metavar="file", required=FALSE)
args$add_argument("--SPOTlightSCclusterMarkers", default="SPOTlight_sc_cluster_markers.csv", help="dir", metavar="file", required=FALSE)

args <- parser$parse_args()


# Main script
set.seed(123)
#np <- import("numpy")
normDataDir <- args$filePath

filename <- list.files(path=args$outsPath, pattern=args$fileh5)[1]
print(args$outsPath)


library("jsonlite")
library("png")

Read10X_Image <- function(image.dir, image.name = "tissue_lowres_image.png", filter.matrix = TRUE, ...) {
  image <- readPNG(source = file.path(image.dir, image.name))
  scale.factors <- fromJSON(txt = file.path(image.dir, 'scalefactors_json.json'))
  tissue.positions.path <- Sys.glob(paths = file.path(image.dir, 'tissue_positions*'))
  print("Reading tissue positions")
  print(tissue.positions.path)
  tissue.positions <- read.csv(
    file = tissue.positions.path,
    col.names = c('barcodes', 'tissue', 'row', 'col', 'imagerow', 'imagecol'),
    header = ifelse(
      test = basename(tissue.positions.path) == "tissue_positions.csv",
      yes = TRUE,
      no = FALSE
    ),
    as.is = TRUE,
    row.names = 1
  )
  print("Filtering matrix")
  if (filter.matrix) {
    tissue.positions <- tissue.positions[which(x = tissue.positions$tissue == 1), , drop = FALSE]
  }
  print("Parsing json")
  unnormalized.radius <- scale.factors$fiducial_diameter_fullres * scale.factors$tissue_lowres_scalef
  spot.radius <-  unnormalized.radius / max(dim(x = image))
  return(new(
    Class = 'VisiumV1',
    image = image,
    scale.factors = scalefactors(
      spot = scale.factors$tissue_hires_scalef,
      fiducial = scale.factors$fiducial_diameter_fullres,
      hires = scale.factors$tissue_hires_scalef,
      scale.factors$tissue_lowres_scalef
    ),
    coordinates = tissue.positions,
    spot.radius = spot.radius
  ))
}


if (TRUE) {
#    print(filename)
#    se_st <- Seurat::Load10X_Spatial(data.dir = args$outsPath, filename = filename)
#} else {
    print("Reading 10x image")
    print(file.path(args$outsPath, 'spatial'))
    image <- Read10X_Image(image.dir=file.path(args$outsPath, 'spatial'), filter.matrix=TRUE)
    print("Done reading 10x image")
    print(paste0(args$outsPath, args$outsSubDir))
    m <- Read10X(paste0(args$outsPath, args$outsSubDir), gene.column=args$mtxGeneColumn)
    m <- m[,row.names(image@coordinates)]
    m <- m[,colSums(m)>0]
    se_st <- CreateSeuratObject(counts=m, assay="Spatial")
    image <- image[Cells(x=se_st)]
    DefaultAssay(object=image) <- "Spatial"
    se_st[["slice1"]] <- image
}

print("Reading ST matrix")
print(paste0(normDataDir, args$nameX))
matrix_st <- data.matrix(read.csv(paste0(normDataDir, args$nameX), row.names=1))

print(paste0(normDataDir, args$nameVar))
st_genes <- read.csv(paste0(normDataDir, args$nameVar))$X

print(paste0(normDataDir, args$nameObs))
st_obs <- read.csv(paste0(normDataDir, args$nameObs))$X

print("Done reading ST")
rownames(matrix_st) <- st_genes
colnames(matrix_st) <- st_obs
matrix_st <- as(exp(matrix_st) - 1, "sparseMatrix")
se_st@assays$Spatial@counts <- matrix_st
se_st@assays$Spatial@data <- matrix_st
#se_st@assays$Spatial@counts <- as((args$countsFactor)*matrix_st, "sparseMatrix")
#se_st@assays$Spatial@data <- as((args$countsFactor)*matrix_st, "sparseMatrix")

# Need to check if null or empty
print(args$annoDataDir)
print(args$annoDataDir=='')

if (args$annoDataDir=='') {
    #matrix_sc <- np$load(paste0(normDataDir, args$SCnameX))[['arr_0']]
    print(paste0(normDataDir, args$SCnameX))
    print(paste0(normDataDir, args$SCnameVar))
    print(paste0(normDataDir, args$SCnameObs))
    
    matrix_sc <- data.matrix(read.csv(paste0(normDataDir, args$SCnameX), row.names=1))
    sc_genes <- read.csv(paste0(normDataDir, args$SCnameVar))
    sc_obs <- read.csv(paste0(normDataDir, args$SCnameObs))
    rownames(matrix_sc) <- get(colnames(sc_genes)[1], sc_genes)
    colnames(matrix_sc) <- get(colnames(sc_obs)[1], sc_obs)
    se_sc <- Seurat::CreateSeuratObject(counts = as(exp(matrix_sc) - 1, "sparseMatrix"))
    #se_sc <- Seurat::CreateSeuratObject(counts = as((args$countsFactor)*matrix_sc, "sparseMatrix"))
    
    # Cluster sc data
    se_sc <- Seurat::FindVariableFeatures(se_sc, verbose = FALSE)
    se_sc <- Seurat::ScaleData(se_sc, verbose = FALSE)
    se_sc <- Seurat::RunPCA(se_sc, verbose = FALSE)
    se_sc <- Seurat::RunUMAP(se_sc, dims = 1:30, verbose = FALSE)
    se_sc <- Seurat::FindNeighbors(se_sc)
    se_sc <- Seurat::FindClusters(se_sc, resolution=args$clusterResolution)
    Seurat::DimPlot(se_sc, group.by = "seurat_clusters", label = TRUE) + Seurat::NoLegend()
    ggsave(paste0(args$filePath, args$SPOTlightSCclustersName), dpi=600, scale=0.5, width=8, height=8, units='in')
} else {
    print(args$annoDataDir)
    print(args$annoFileCelltype)
    print(args$annoFileCounts)
    
    matrix_sc <- data.matrix(t(read.csv(paste0(args$annoDataDir, args$annoFileCounts), row.names=1)))
    se_sc <- Seurat::CreateSeuratObject(counts=as(matrix_sc, "sparseMatrix"))
    
    ct <- read.csv(paste0(args$annoDataDir, args$annoFileCelltype), row.names=1)[['Celltype']]
    Seurat::Idents(object=se_sc) <- ct
    se_sc <- Seurat::AddMetaData(se_sc, ct, col.name="seurat_clusters")
    se_sc <- Seurat::ScaleData(se_sc)
}


if (TRUE) {   
    cluster_markers_all <- Seurat::FindAllMarkers(object=se_sc, assay=NULL, slot="data", test.use="wilcox", only.pos=TRUE)
    write.csv(cluster_markers_all, file=paste0(args$filePath, args$SPOTlightSCclusterMarkers))
    
    spotlight_ls <- SPOTlight::spotlight_deconvolution(
      se_sc = se_sc,				# Single cell dataset
      counts_spatial = se_st@assays$Spatial@counts,	# Spatial dataset count
      clust_vr = "seurat_clusters", 		# Variable in sc_sc containing the cell-type annotation
      cluster_markers = cluster_markers_all, 	# Dataframe with the marker genes
      cl_n = args$numberCellsPerCelltype, 					# Number of cells per cell type to use
      hvg = args$numberHVG, 					# Number of HVG to use
      ntop = NULL, 					# Number of top marker genes to use (by default all)
      transf = "uv", 				# Perform unit-variance scaling per cell and spot prior to factorzation and NLS
      method = "nsNMF", 				# Factorization method
      min_cont = 0)					# Remove those cells contributing to a spot below a certain threshold 

    saveRDS(object = spotlight_ls, file = paste0(args$filePath, args$NMFsaveFile))
} else {
    spotlight_ls <- readRDS(file = paste0(args$filePath, args$NMFsaveFile))
}

# NMF topic profiles
nmf_mod <- spotlight_ls[[1]]
h <- NMF::coef(nmf_mod[[1]])
rownames(h) <- paste("Topic", 1:nrow(h), sep = "_")
topic_profile_plts <- SPOTlight::dot_plot_profiles_fun(h = h, train_cell_clust = nmf_mod[[2]])
topic_profile_plts[[2]] + ggplot2::theme(axis.text.x = ggplot2::element_text(angle = 0), axis.text = ggplot2::element_text(size = 12))
ggsave(paste0(args$filePath, args$SPOTlightTopicsName), dpi=300, scale=0.5, width=10, height=8, units='in')

# Add deconvolution results to se_st meta.data
decon_mtrx <- spotlight_ls[[2]]
decon_mtrx_sub <- decon_mtrx[, colnames(decon_mtrx)!="res_ss"]
decon_mtrx_sub[decon_mtrx_sub < 0.08] <- 0
decon_mtrx <- cbind(decon_mtrx_sub, "res_ss" = decon_mtrx[, "res_ss"])
rm(decon_mtrx_sub)

rownames(decon_mtrx) <- colnames(se_st) 
decon_df <- decon_mtrx %>% data.frame() %>% tibble::rownames_to_column("barcodes")

se_st@meta.data <- se_st@meta.data %>% tibble::rownames_to_column("barcodes") %>% dplyr::left_join(decon_df, by = "barcodes") %>% tibble::column_to_rownames("barcodes")

# Individual cell types on image
#Seurat::SpatialFeaturePlot(object = se_st, features = colnames(decon_df)[-1][-length(colnames(decon_df))+1], alpha = c(0.1, 1), min.cutoff=0, max.cutoff=0.3, crop = FALSE, pt.size.factor=1.0)
#ggsave(paste0(args$filePath, args$SPOTlightFeaturesName), dpi=500, scale=1.25, width=8, height=8, units='in')

#cell_types_all <- colnames(decon_mtrx)[which(colnames(decon_mtrx) != "res_ss")]
#cell_types_all <- paste("X", cell_types_all, sep = "")
#SPOTlight::spatial_scatterpie(se_obj = se_st, cell_types_all = cell_types_all,
#                              img_path = paste0(args$outsPath, args$imagePath),
#                              cell_types_interest = NULL, slice = NULL, scatterpie_alpha = 1, pie_scale = args$SPOTlightScatterpiesSize)
#ggsave(paste0(args$filePath, args$SPOTlightScatterpiesName), dpi=600, scale=1.0, width=8, height=8, units='in')


# Remove cell types not predicted to be on the tissue
decon_mtrx_sub <- decon_mtrx[, colnames(decon_mtrx)[which(colnames(decon_mtrx) != "res_ss")]]
decon_mtrx_sub <- decon_mtrx_sub[, colSums(decon_mtrx_sub) > 0]
colnames(decon_mtrx_sub) <- paste("X", colnames(decon_mtrx_sub), sep = "")
decon_cor <- cor(decon_mtrx_sub)
p.mat <- corrplot::cor.mtest(mat = decon_mtrx_sub, conf.level = 0.95)

## Visualize
#ggcorrplot::ggcorrplot(corr = decon_cor, p.mat = p.mat[[1]], hc.order = TRUE, type = "full", insig = "blank",
#  lab = TRUE, outline.col = "lightgrey", method = "square", colors = c("#6D9EC1", "white", "#E46726"),
#  title = "Cell type proportions correlation", 
#  legend.title = "Correlation\n(Pearson)") +
#  ggplot2::theme(plot.title = ggplot2::element_text(size = 22, hjust = 0.5, face = "bold"),
#    legend.text = ggplot2::element_text(size = 12), legend.title = ggplot2::element_text(size = 15),
#    axis.text.x = ggplot2::element_text(angle = 90), axis.text = ggplot2::element_text(size = 18, vjust = 0.5))
#ggsave(paste0(args$filePath, args$SPOTlightCorrName), dpi=600, scale=0.75, width=8, height=8, units='in')

write.csv(decon_df, file=paste0(args$filePath, args$SPOTlightPropNorm))
# There was some error need to test this output
write.csv(cbind(cluster_id=nmf_mod[[2]], h), file=paste0(args$filePath, args$SPOTlightBetaNorm))

#write.csv(se_sc@active.ident, file=paste0(args$filePath, args$SPOTlightSCclusterIds))
#write.csv(se_sc@reductions[["pca"]]@cell.embeddings, file=paste0(args$filePath, args$SPOTlightSCpca))
#write.csv(se_sc@reductions[["pca"]]@feature.loadings, file=paste0(args$filePath, args$SPOTlightSCloadings))

quit(status=0)
