import os
import re
import sys
import yaml
import shutil
import argparse
import pandas as pd
from Bio import SeqIO
from Bio.SeqRecord import SeqRecord

if os.path.exists('orthogroups'):
    shutil.rmtree('orthogroups')

if not os.path.exists('orthogroups'):
    os.mkdir('orthogroups')


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--config',
        type=argparse.FileType(mode='r'),
        default='config.yaml', 
        help='The config file to use. Must be placed in the root folder.',
    )

    args = parser.parse_args()
    if args.config:
        data = yaml.load(args.config, Loader=yaml.FullLoader)
        arg_dict = args.__dict__

        for key, value in data.items():
            arg_dict[key] = value

    return args


def map_gene_to_prot_id(
    cds_path: str, 
    gene_re=r'\[gene=(.*?)\]', 
    prot_id_re=r'\[protein_id=(.*?)\]'
    ) -> dict:

    map: dict[str, str] = dict()
    cds = list(SeqIO.parse(open(cds_path), 'fasta'))

    for record in cds:
        gene_match = re.search(gene_re, record.description)

        if gene_match:
            prot_id = re.search(prot_id_re, record.description)
            
            if prot_id:
                map[gene_match.group(1)] = prot_id.group(1)
            else:
                map[gene_match.group(1)] = ''

    return map


def main() -> int:
    args = parse_arguments()

    ortho_path = args.ortho_path
    output_directory = 'orthogroups'

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    print('Reading Orthogroups from {path}'.format(
        path=ortho_path,
    ))
    df = pd.read_csv(ortho_path, sep='\t', low_memory=False)

    # Get the names of dropped columns
    dropped_columns = df.columns[df.eq('Not found').all()].tolist()
    df = df.drop(dropped_columns, axis=1)
    
    print('Read {n} rows.'.format(n=len(df)))

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    ref_species_path = os.path.join(args.cds_directory, args.reference_species + '_cds.fna')
    gene_to_prot_id = map_gene_to_prot_id(ref_species_path)
    prot_id_to_gene = {v:k for k, v in gene_to_prot_id.items() if k in args.gene_names}

    count = 0
    d = dict()
    for idx, c in enumerate(df.columns[1:]):
        if idx % 100 == 0:
            print(f'{idx}...')

        f_name = c + '_cds.fna'

        cds_path = os.path.join(args.cds_directory, f_name)

        if not os.path.exists(cds_path):
            dropped_columns.append(c)
            continue

        records = list(SeqIO.parse(open(cds_path), 'fasta'))

        records_to_write = list()
        prot_id_re = r'\[protein_id=(.*?)\]'
        for record in records:
            prot_id_match = re.search(prot_id_re, record.description)

            if prot_id_match:
                prot_id = prot_id_match.group(1)

                if prot_id in df[c].values.tolist():
                    ortho_to_prot_id = df.loc[df[c] == prot_id]['Orthogroup'].values[0]
                    ortho_to_name = prot_id_to_gene[ortho_to_prot_id]
            
                    d.setdefault(c, list()).append(prot_id)

                    records_to_write.append(SeqRecord(
                        record.seq,
                        id=prot_id,
                        description=(record.description + ' ' + '[orthologous_to_gene=' + ortho_to_name + '] [orthologous_to_ref_protein=' + ortho_to_prot_id + '] [ref_species=' + args.reference_species + ']'),
                    ))

        output_path = os.path.join(output_directory, f_name)

        count += len(records_to_write)
        with open(output_path, 'w') as f:
            SeqIO.write(records_to_write, f, 'fasta')

    print('Wrote', count, 'genes.')

    input_species_file = args.input_species_directory

    df = pd.read_csv(input_species_file)
    df = df.drop(df[df['species_name'].isin(dropped_columns)].index.tolist()).reset_index(drop=True)
    df.to_csv('../../../data/fourdbs_concat/fourdbs_input_species.csv', index=False)
    df.to_csv('fourdbs_input_species.csv', index=False)

    print('Done. See file data/fourdbs_concat/fourdbs_input_species.csv. Use this as input to ALLEGRO in config.yaml')

    return 0


if __name__ == '__main__':
    sys.exit(main())