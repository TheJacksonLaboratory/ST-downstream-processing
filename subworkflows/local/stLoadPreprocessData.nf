nextflow.enable.dsl=2

/* 
 * Include requires tasks 
 */
include { READ_ST_AND_SC_SCANPY     } from '../../modules/local/tasks'
include { NORMALIZATION  } from '../../modules/local/tasks'
include { ST_PREPROCESS             } from '../../modules/local/tasks'
include { SC_PREPROCESS             } from '../../modules/local/tasks'

/* 
 * Definition of Preprocessing Workflow
 */
workflow ST_LOAD_PREPROCESS_DATA {
 
    take:
      sample_ids
      outdir
      
    main:
      READ_ST_AND_SC_SCANPY(       sample_ids,                   outdir)
      NORMALIZATION(               READ_ST_AND_SC_SCANPY.out,    outdir)
      ST_PREPROCESS(               NORMALIZATION.out, outdir)
      SC_PREPROCESS(               NORMALIZATION.out, outdir)
      
    emit:
      ST_PREPROCESS.out
      .join(SC_PREPROCESS.out)
      
 }
