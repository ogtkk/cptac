#   Copyright 2018 Samuel Payne sam_payne@byu.edu
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#       http://www.apache.org/licenses/LICENSE-2.0
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import pandas as pd
import os
from cptac.cancers.source import Source

class BcmUcec(Source):
    """The BcmUcec class is inherited from the Source class. It manages the loading of the UCEC data from the BCM source."""

    def __init__(self, no_internet=False):
        """
        Initializes the BcmUcec object.

        Parameters:
        no_internet (bool, optional): If True, skip the index update step. Useful when internet connection is spotty or not available. Default is False.
        """

        # Define the data files associated with this dataset
        self.data_files = {
            "mapping" : "gencode.v34.basic.annotation-mapping.txt.gz",
            "circular_RNA" : "UCEC-circRNA_rsem_tumor_normal_UQ_log2(x+1)_BCM.txt.gz",
            "transcriptomics" : "UCEC-gene_rsem_removed_circRNA_tumor_normal_UQ_log2(x+1)_BCM.txt.gz",
            "proteomics" : ["UCEC_proteomics_gene_abundance_log2_reference_intensity_normalized_Tumor.txt.gz","UCEC_proteomics_gene_abundance_log2_reference_intensity_normalized_Normal.txt.gz"],
            "phosphoproteomics" : ["UCEC_phospho_site_abundance_log2_reference_intensity_normalized_Tumor.txt","UCEC_phospho_site_abundance_log2_reference_intensity_normalized_Normal.txt.gz"],
            "CNV" : "UCEC_WES_CNV_gene_ratio_log2.txt.gz",
            "miRNA" : "UCEC_miRNAseq_mature_miRNA_RPM_log2_Tumor.txt.gz"
        }
        
        # Define the load functions for each data type
        self.load_functions = {
            'circular_RNA' : self.load_circular_RNA,
            'transcriptomics' : self.load_transcriptomics,
            'proteomics' : self.load_proteomics,
            'phosphoproteomics' : self.load_phosphoproteomics,
            'CNV' : self.load_CNV,
            'miRNA' : self.load_miRNA
        }
        
        # Initialize the Source parent class
        super().__init__(cancer_type="ucec", source='bcm', data_files=self.data_files, load_functions=self.load_functions, no_internet=no_internet)

    def load_circular_RNA(self):
        """Loads the circular RNA data, processes it by adding gene names and formatting, and stores it within the object."""

        df_type = 'circular_RNA'
        
        if df_type not in self._data:
            # If the data is not already loaded, load it
            file_path = self.locate_files(df_type)
            
            df = pd.read_csv(file_path, sep="\t")
            df = df.rename_axis('INDEX').reset_index()
            df[["circ","chrom","start","end","gene"]] = df.INDEX.str.split('_', expand=True)
            df["circ_chromosome"] = df["circ"] +"_" + df["chrom"]
            df = df.set_index('gene')
            
            # Add gene names to circular RNA data
            self.load_mapping()
            gene_key = self._helper_tables["gene_key"]
            df = gene_key.join(df, how = "inner")
            df = df.reset_index()
            df = df.rename(columns= {"gene_name": "Name","gene":"Database_ID"}) # change names to match cptac package
            df = df.set_index(["Name","circ_chromosome", "start","end","Database_ID"]) #create multi-index
            df.drop(['INDEX', 'circ', 'chrom'], axis=1, inplace=True) 
            df = df.sort_index()
            df = df.T
            df.index = df.index.str.replace(r"_T", "", regex=True) # remove Tumor label
            df.index = df.index.str.replace(r"_A", ".N", regex=True)# Normal samples labeled with .N
            df.index.name = "Patient_ID"

            # save df in self._data
            self.save_df(df_type, df)

    def load_mapping(self):
        """Loads the gene to gene_name mapping data and stores it within the object for later use."""

        df_type = 'mapping'

        if not self._helper_tables:
            # If the mapping data is not already loaded, load it
            file_path = self.locate_files(df_type)
            
            df = pd.read_csv(file_path, sep="\t")
            df = df[["gene","gene_name"]] #only need gene (database gene id) and gene_name (common gene name)
            df = df.set_index("gene")
            df = df.drop_duplicates()
            self._helper_tables["gene_key"] = df

    def load_transcriptomics(self):
        """Loads the transcriptomics data, adds gene names, formats the data, and stores it within the object."""

        df_type = 'transcriptomics'

        if df_type not in self._data:
            # If the data is not already loaded, load it
            file_path = self.locate_files(df_type)
            
            df = pd.read_csv(file_path, sep="\t")
            df.index.name = 'gene'
            
            # Add gene names to transcriptomic data
            self.load_mapping()
            gene_key = self._helper_tables["gene_key"]
            transcript = gene_key.join(df, how = "inner") #keep only gene_ids with gene names
            transcript = transcript.reset_index()
            transcript = transcript.rename(columns={"gene_name":"Name","gene":"Database_ID"})
            transcript = transcript.set_index(["Name", "Database_ID"])
            transcript = transcript.sort_index() #alphabetize
            transcript = transcript.T
            transcript.index = transcript.index.str.replace(r"_T", "", regex=True)
            transcript.index = transcript.index.str.replace(r"_A", ".N", regex=True)# Normal samples labeled with .N
            transcript.index.name = "Patient_ID"

            df = transcript
            # save df in self._data
            self.save_df(df_type, df)


    def load_proteomics(self):
        """
        Load and parse all files for bcm brca proteomics data
        """
        df_type = 'proteomics'

        # Check if data is already loaded
        if df_type not in self._data:
            # Get file path to the correct data
            file_path_list = self.locate_files(df_type)
            # Loop over list of file paths to load each type of proteomics data (tumor/normal)
            for file_path in file_path_list:
                file_name = os.path.basename(file_path)

                # Load and process the files
                if file_name == "UCEC_proteomics_gene_abundance_log2_reference_intensity_normalized_Tumor.txt.gz":
                    df = pd.read_csv(file_path, sep='\t')
                    df.index.name = 'gene'

                    df.set_index('idx', inplace=True)

                    # Load mapping information
                    self.load_mapping()
                    gene_key = self._helper_tables["gene_key"]
                    # Join gene_key to df, reset index, rename columns, set new index and sort
                    tumor_proteomics = gene_key.join(df, how='inner')
                    tumor_proteomics = gene_key.join(df, how='inner')
                    tumor_proteomics = tumor_proteomics.reset_index()
                    tumor_proteomics = tumor_proteomics.rename(columns={"index": "Database_ID", "gene_name": "Name"})
                    tumor_proteomics = tumor_proteomics.set_index(["Name", "Database_ID"])
                    tumor_proteomics = tumor_proteomics.sort_index()  # alphabetize
                    tumor_proteomics = tumor_proteomics.T
                    tumor_proteomics.index.name = "Patient_ID"

                    df = tumor_proteomics

                    self._helper_tables["proteomics_tumor"] = df


                if file_name == "UCEC_proteomics_gene_abundance_log2_reference_intensity_normalized_Normal.txt.gz":
                    df = pd.read_csv(file_path, sep='\t')
                    df.index.name = 'gene'

                    df.set_index('idx', inplace=True)
                    # Load mapping information
                    self.load_mapping()
                    gene_key = self._helper_tables["gene_key"]

                    # Join gene_key to df, reset index, rename columns, set new index and sort
                    normal_proteomics = gene_key.join(df, how='inner')
                    normal_proteomics = gene_key.join(df, how='inner')
                    normal_proteomics = normal_proteomics.reset_index()
                    normal_proteomics = normal_proteomics.rename(columns={"index": "Database_ID", "gene_name": "Name"})
                    normal_proteomics = normal_proteomics.set_index(["Name", "Database_ID"])
                    normal_proteomics = normal_proteomics.sort_index()  # alphabetize
                    normal_proteomics = normal_proteomics.T
                    normal_proteomics.index.name = "Patient_ID"
                    modified_index = [label + '.N' for label in normal_proteomics.index]
                    normal_proteomics.index = modified_index

                    df = normal_proteomics

                    self._helper_tables["proteomics_normal"] = df

            # Combine the two proteomics dataframes
            prot_tumor = self._helper_tables.get("proteomics_tumor")
            prot_normal = self._helper_tables.get("proteomics_normal") 
            prot_combined = pd.concat([prot_tumor, prot_normal])

            # Save df in data
            self.save_df(df_type, prot_combined)

    def load_phosphoproteomics(self):
        """
        Load and parse all files for bcm brca phosphoproteomics data
        """
        df_type = 'phosphoproteomics'

        # Check if data is already loaded
        if df_type not in self._data:
            # Get file path to the correct data
            file_path_list = self.locate_files(df_type)

            for file_path in file_path_list:

                file_name = os.path.basename(file_path)

                if file_name == "UCEC_phospho_site_abundance_log2_reference_intensity_normalized_Tumor.txt":
                    # Load and process the file
                    df = pd.read_csv(file_path, sep='\t')
                    df.index.name = 'gene'

                    # Extract Database_ID, gene name, site, and peptide from 'idx' column
                    df[['ENSG', 'ENSP', 'Site', 'Sequence', 'Number']] = df['idx'].str.split('|', expand=True).iloc[:,
                                                                         [0, 1, 2, 3, 4]]

                    # Load mapping information
                    self.load_mapping()
                    gene_key_df = self._helper_tables["gene_key"]
                    mapping = gene_key_df['gene_name'].to_dict()

                    # Map gene_key to get gene name
                    df['Name'] = df['ENSG'].map(mapping)

                    # Drop the 'idx' and 'Gene_Key' columns
                    df.drop(columns=['idx'], inplace=True)

                    # Set the 'Name', 'Site', 'Peptide', and 'Database_ID' columns as index in this order
                    df.set_index(['Name', 'Site', 'Sequence', 'ENSG', 'ENSP', 'Number'], inplace=True)
                    # Transpose the dataframe so that the patient IDs are the index
                    df = df.transpose()

                    # Rename the index to 'Patient_ID'
                    df.index.name = 'Patient_ID'

                    self._helper_tables["phosphoproteomics_tumor"] = df

                if file_name == "UCEC_phospho_site_abundance_log2_reference_intensity_normalized_Normal.txt.gz":
                    # Load and process the file
                    df = pd.read_csv(file_path, sep='\t')
                    df.index.name = 'gene'

                    # Extract Database_ID, gene name, site, and peptide from 'idx' column
                    df[['ENSG', 'ENSP', 'Site', 'Sequence', 'Number']] = df['idx'].str.split('|', expand=True).iloc[:,
                                                                         [0, 1, 2, 3, 4]]

                    # Load mapping information
                    self.load_mapping()
                    gene_key_df = self._helper_tables["gene_key"]
                    mapping = gene_key_df['gene_name'].to_dict()

                    # Map gene_key to get gene name
                    df['Name'] = df['ENSG'].map(mapping)

                    # Drop the 'idx' and 'Gene_Key' columns
                    df.drop(columns=['idx'], inplace=True)

                    # Set the 'Name', 'Site', 'Peptide', and 'Database_ID' columns as index in this order
                    df.set_index(['Name', 'Site', 'Sequence', 'ENSG', 'ENSP', 'Number'], inplace=True)

                    # Transpose the dataframe so that the patient IDs are the index
                    df = df.transpose()

                    # Rename the index to 'Patient_ID'
                    df.index.name = 'Patient_ID'
                    modified_index = [label + '.N' for label in df.index]
                    df.index = modified_index
                    self._helper_tables["phosphoproteomics_normal"] = df

            # Combine the two proteomics dataframes
            phospho_tumor = self._helper_tables.get("phosphoproteomics_tumor")
            phospho_normal = self._helper_tables.get("phosphoproteomics_normal")

            # Concatenate the two DataFrames
            phospho_combined = pd.concat([phospho_tumor, phospho_normal])

            # Save df in data
            self.save_df(df_type, phospho_combined)

    def load_CNV(self):
        """Loads and processes the CNV data file, and stores it within the object."""
        df_type = 'CNV'
        # Check if data is already loaded
        if df_type not in self._data:
            # Get file path to the correct data
            file_path = self.locate_files(df_type)

            # Load and process the file
            df = pd.read_csv(file_path, sep='\t')
            df.index.name = 'gene'

            df.set_index('idx', inplace=True)
            # Load mapping information
            self.load_mapping()
            gene_key = self._helper_tables["gene_key"]

            # Join gene_key to df, reset index, rename columns, set new index and sort
            df = gene_key.join(df, how='inner')
            df = df.reset_index()
            df = df.rename(columns={"index": "Database_ID", "gene_name": "Name"})
            df = df.set_index(["Name", "Database_ID"])
            df = df.sort_index()  # alphabetize
            df = df.T
            df.index.name = "Patient_ID"

            # Save df in data
            self.save_df(df_type, df)

    def load_miRNA(self):
        """
        Load and parse all files for miRNA data
        """
        df_type = 'miRNA'

        # Check if data is already loaded
        if df_type not in self._data:
            # Get file path to the correct data
            file_path = self.locate_files(df_type)

            # Load and process the file
            df = pd.read_csv(file_path, sep='\t')

            # Here the idx will be the miRNA names and columns will be the patient IDs.
            df.set_index('idx', inplace=True)
            df.index.name = 'Name'  # Rename idx to Name
            df = df.transpose()  # Transpose the data frame to have miRNA as columns and patients as rows
            df.index.name = "Patient_ID"

            # Save df in data
            self.save_df(df_type, df)
