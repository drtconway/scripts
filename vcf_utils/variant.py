from collections import OrderedDict
from statistics import mean, stdev


BAM_STATS_LINES = ['##FORMAT=<ID=PMCDP,Number=1,Type=Integer,Description="Total \
read depth (includes bases supporting other alleles) - Calculated By \
Bioinformatics Dept">\n',
                   '##FORMAT=<ID=PMCRD,Number=1,Type=Integer,Description="Depth \
of reference-supporting bases - Calculated By Bioinformatics Dept">\n',
                   '##FORMAT=<ID=PMCAD,Number=A,Type=Integer,Description="Depth \
of alternate-supporting bases - Calculated By Bioinformatics Dept">\n',
                   '##FORMAT=<ID=PMCFREQ,Number=A,Type=Float,Description="Variant \
allele frequency - Calculated By Bioinformatics Dept">\n',
                   '##FORMAT=<ID=PMCRDF,Number=1,Type=String,Description="Depth \
of reference-supporting bases on forward strand - Calculated By \
Bioinformatics Dept">\n',
                   '##FORMAT=<ID=PMCRDR,Number=1,Type=String,Description="Depth \
of reference-supporting bases on reverse strand - Calculated By \
Bioinformatics Dept">\n',
                   '##FORMAT=<ID=PMCADF,Number=A,Type=String,Description="Depth \
of alternate-supporting bases on forward strand - Calculated By \
Bioinformatics Dept">\n',
                   '##FORMAT=<ID=PMCADR,Number=A,Type=String,Description="Depth \
of alternate-supporting bases on reverse strand - Calculated By \
Bioinformatics Dept">\n',
                   '##FORMAT=<ID=PMCBDIR,Number=A,Type=String,Description="Y/N \
indicating if variant is bidirectional (N/A if no alt reads) - Calculated By \
Bioinformatics Dept">\n']


###############################################################################


def normalise_GT(old_gt):
    gt = old_gt.replace('.', '0'.replace('|', '/'))
    if ('1/0' in gt) or ('1/0' in gt):
        gt = '0/1'
    else:
        pass
    return gt


def cal_AD(AD):
    """Calculate the average and sd of AD
    """
    # Remove the AD if missing in specific caller
    AD = [k for k in AD if k != '.']
    if AD == []:
        col_mean, col_sd = '.,.', '.,.'
    else:
        AD = [[int(i) for i in v.split(',')] for v in AD]
        if len(AD) == 1:
            col_mean, col_sd = ','.join(str(i) for i in AD[0]), '.,.'
        else:
            col_mean = ','.join([str(i) for i in map(lambda x: round(mean(x),
                                 ), zip(*AD))])
            col_sd = ','.join([str(i) for i in map(lambda x: round(stdev(x),
                              2), zip(*AD))])
    return col_mean, col_sd

def cal_DP(DP):
    """Calculate the average and sd of DP
    """
    # Remove the DP if missing
    DP = [k for k in DP if k != '.']
    if DP == []:
        col_mean, col_sd = '.', '.'
    else:
        DP = [int(v) for v in DP]
        if len(DP) == 1:
            col_mean, col_sd = str(DP[0]), '.'
        else:
            col_mean, col_sd = str(round(mean(DP))), str(round(stdev(DP), 2))

    return col_mean, col_sd

###############################################################################


class Variant:
    """
    """

    def __init__(self):
        """
        """
        self.chr = ''
        self.pos = ''
        self.ref = ''
        self.alt = ''
        self.sample_id = ''
        self.qual = ''
        self.filter = ''
        self.mandatory = []
        self.info, self.format = OrderedDict(), OrderedDict()

    def process_variant(self, line, caller):
        """Create variant from line (with processing of GT and AF)
        """
        line = line.strip().split('\t')
        self.chr = line[0]
        self.pos = line[1]
        self.sample_id = line[2]
        self.ref = line[3]
        self.alt = line[4]
        self.qual = line[5]
        self.filter = line[6]
        self.mandatory = line[:7]
        self.variant_key = '\t'.join(line[:2] + line[3:5])
        for i in line[7].split(';'):
            try:
                self.info[i.split('=')[0]] = i.split('=')[1]
            except:
                self.info[i] = i
        for name, val in zip(line[8].split(':'), line[9].split(':')):
            self.format[name] = val

        # Normalise GT
        self.format['GT'] = normalise_GT(self.format['GT'])

        # Get AF and DP
        if caller == 'strelka':
            # use DPI as DP for INDELs in strelka
            if not len(self.ref) == len(self.alt) == 1:
                self.format['DP'] = self.format.get("DPI", ".")

        # Calculate the allele frequency regardless
        try:
            self.info['AF'] = str(round(float(self.format['AD'].split(',')
                                  [1]) / float(self.format['DP']), 2))
        except:
            self.info['AF'] = '.'

        # Replace the AD / DP values in INFO with FORMAT
        if 'AD' in self.format.keys():
            self.info['AD'] = self.format['AD']
        if 'DP' in self.format.keys():
            self.info['DP'] = self.format['DP']
        return self

    def process_somatic_variant(self, line, caller, n_index, t_index):
        """Create somatic variant from line (with normalisation of GT)
        """

        line = line.strip().split('\t')
        self.chr = line[0]
        self.pos = line[1]
        self.sample_id = line[2]
        self.ref = line[3]
        self.alt = line[4]
        self.qual = line[5]
        self.filter = line[6]
        self.mandatory = line[:7]
        self.variant_key = '\t'.join(line[:2] + line[3:5])
        normal_dict, tumor_dict = OrderedDict(), OrderedDict()

        # Prevent the single tag situation, like "SOMATIC;" (in strelka)
        for i in line[7].split(';'):
            try:
                self.info[i.split('=')[0]] = i.split('=')[1]
            except:
                self.info[i] = i
        for name, val in zip(line[8].split(':'), line[n_index].split(':')):
            normal_dict[name] = val
        for name, val in zip(line[8].split(':'), line[t_index].split(':')):
            tumor_dict[name] = val

        # Normalise GT (no GT in strelka)
        if caller == 'strelka':
            pass
        else:
            normal_dict['GT'] = normalise_GT(normal_dict['GT'])
            tumor_dict['GT'] = normalise_GT(tumor_dict['GT'])

        # self.foramt would be a dict containing two dicts, normal and tumor
        self.format['normal'] = normal_dict
        self.format['tumor'] = tumor_dict

        return self

    def read_variant(self, line, somatic=False, normal=None, tumor=None):
        """Create variant from line (no processing)
        """

        line = line.strip().split('\t')
        self.chr = line[0]
        self.pos = line[1]
        self.sample_id = line[2]
        self.ref = line[3]
        self.alt = line[4]
        self.qual = line[5]
        self.filter = line[6]
        self.mandatory = line[:7]
        self.variant_key = '\t'.join(line[:2] + line[3:5])

        for i in line[7].split(';'):
            try:
                self.info[i.split('=')[0]] = i.split('=')[1]
            except:
                self.info[i] = i

        if not somatic:
            for name, val in zip(line[8].split(':'), line[9].split(':')):
                self.format[name] = val
        else:
            normal_dict, tumor_dict = OrderedDict(), OrderedDict()
            for name, val in zip(line[8].split(':'), line[normal].split(':')):
                normal_dict[name] = val
            for name, val in zip(line[8].split(':'), line[tumor].split(':')):
                tumor_dict[name] = val
            self.format['normal'] = normal_dict
            self.format['tumor'] = tumor_dict

        return self

    def select_info(self, i_dict, f_dict, caller=None, somatic=False):
        """ Update the variant with the selected columns
        Input:
            new info, format dictionary {col: header object}
        Output:
            updated variant with selected info/format values
        """
        new_info, new_format = OrderedDict(), OrderedDict()

        if not somatic:
            for k, v in i_dict.items():
                info = self.info.get(k, '.')
                if info:
                    new_info[v.meta_id] = info
                else:
                    new_info[v.meta_id] = self.format.get(k, '.')
            for k, v in f_dict.items():
                new_format[v.meta_id] = self.format.get(k, '.')

        else:
            new_format['normal'], new_format['tumor'] = OrderedDict(),\
                                                        OrderedDict()
            for k, v in i_dict.items():
                try:
                    # Try if k is a normal column in INFO:
                    new_info[k] = self.info[k]
                except KeyError:
                    # This column has normal / tumor
                    try:
                        if k.endswith('normal'):
                            new_info['{}_{}'.format(k, caller)] = \
                            self.format['normal'][k.strip('_normal')]
                        else:
                            new_info['{}_{}'.format(k, caller)] = \
                            self.format['tumor'][k.strip('_tumor')]
                    except KeyError:
                        pass

            for k, v in f_dict.items():
                try:
                    new_format['normal'][k] = self.format['normal'][k]
                    new_format['tumor'][k] = self.format['tumor'][k]
                except:
                    if k == 'GT':
                        new_format['normal']['GT'] = '.'
                        new_format['tumor']['GT'] = '.'
                    else:
                        pass
        self.info = new_info
        self.format = new_format

        return self

    def combine_info(self, cols, callers, i_dict, somatic=False):
        """ Combine the information, and calculate the mean, sd of AD / DP
        if specified.
        Input: a variant object (the first occurance in the vcfs)
               a list of columns to keep
               a dictionary with combined info columns
        Output: a new variant object
        """
        self.info = i_dict
        new_info_names = ['Identified']
        new_info_vals = ['-'.join(callers)]

        # Calculate AD and DP
        if not somatic:
            if 'AD' in cols:
                AD = [v for k, v in i_dict.items() if k.startswith('AD')]
                col_mean, col_sd = cal_AD(AD)
                new_info_names.extend(['AD_mean', 'AD_sd'])
                new_info_vals.extend([col_mean, col_sd])
                self.format['AD'] = col_mean

            if 'DP' in cols:
                DP = [v for k, v in i_dict.items() if k.startswith('DP')]
                #print(DP)
                col_mean, col_sd = cal_DP(DP)
                new_info_names.extend(['DP_mean', 'DP_sd'])
                new_info_vals.extend([col_mean, col_sd])
                self.format['DP'] = col_mean

        else:
            for i in ['normal', 'tumor']:
                if 'AD' in cols:
                    AD = [v for k, v in i_dict.items() if k.startswith('AD_' + i)]
                    col_mean, col_sd = cal_AD(AD)
                    new_info_names.extend(['AD_mean_'+i, 'AD_sd_'+i])
                    new_info_vals.extend([col_mean, col_sd])
                    self.format[i]['AD'] = col_mean
                if 'DP' in cols:
                    DP = [v for k, v in i_dict.items() if k.startswith('DP_' + i)]
                    col_mean, col_sd = cal_DP(DP)
                    new_info_names.extend(['DP_mean_'+i, 'DP_sd_'+i])
                    new_info_vals.extend([col_mean, col_sd])
                    self.format[i]['DP'] = col_mean                

        # Remove the '.' from AD/DP/AF
        new_info = OrderedDict()
        for k, v in self.info.items():
            if v == "." and ('AD' in k or 'AF' in k or 'DP' in k):
                pass
            else:
                new_info[k] = v

        for name, val in zip(new_info_names, new_info_vals):
            new_info[name] = val
        self.info = new_info
        # Set filter value of combined variant to .
        self.filter = '.'
        return self

    def cal_bam_stats(self, pileup_line):
        """Calculate the bam stats from the pileup line
        """
        if pileup_line:

            pileup = pileup_line[1]
            total_depth = int(pileup_line[0])
            ref_fwd = pileup.count('.')
            ref_rev = pileup.count(',')

            # SNV
            if len(self.ref) == len(self.alt):

                # Recursively remove the indels to avoid counting the indels
                while '-' in pileup:
                    index = pileup.index('-')
                    # check length of indel, which may be multiple characters (>=10)
                    i=1
                    length=""
                    while pileup[index+i] in [str(x) for x in range(0,10)]:
                        length += pileup[index+i]
                        i+=1
                    length = int(length)
                    pileup = pileup[:index] + pileup[index+length+i:]
                while '+' in pileup:
                    index = pileup.index('+')
                    i=1
                    length=""
                    while pileup[index+i] in [str(x) for x in range(0,10)]:
                        length += pileup[index+i]
                        i+=1
                    length = int(length)
                    pileup = pileup[:index] + pileup[index+length+i:]
                alt_fwd = pileup.count(self.alt)
                alt_rev = pileup.count(self.alt.lower())

            # Insertion, eg. ref 'C' alt 'CCA'
            elif len(self.ref) == 1 and len(self.alt) > 1:

                # Look for the pattern +2CA/+2ca (+, length of insertion, bases)
                alt_fwd = pileup.count('+' + str(len(self.alt[1:])) + self.alt[1:])
                alt_rev = pileup.count('+' + str(len(self.alt[1:])) +
                                       self.alt[1:].lower())
                # Recalcualte the reference supporting reads (pileup report the
                # reference match followed by indels)
                ref_fwd -= alt_fwd
                ref_rev -= alt_rev

            elif len(self.ref) > 1 and len(self.alt) == 1:
                alt_fwd = pileup.count('-' + str(len(self.ref[1:])) +
                                       self.ref[1:])
                alt_rev = pileup.count('-' + str(len(self.ref[1:])) +
                                       self.ref[1:].lower())
                ref_fwd -= alt_fwd
                ref_rev -= alt_rev

            else:
                # The MNP and other werid variants
                alt_fwd, alt_rev = 0, 0

            ref_reads = ref_fwd + ref_rev
            alt_reads = alt_fwd + alt_rev

            # Calculate the variant allele frequency and bidirectional
            if alt_reads != 0:
                alt_freq = round(alt_reads / total_depth, 2)
                if alt_fwd != 0 and alt_rev != 0:
                    bidir = 'Y'
                else:
                    bidir = 'N'
            else:
                alt_freq, bidir = '.', 'N/A'

        else:
            total_depth, ref_reads, alt_reads, alt_freq = 0, 0, 0, '.'
            ref_fwd, ref_rev, alt_fwd, alt_rev, bidir = 0, 0, 0, 0, 'N/A'

        bam_stats = [total_depth, ref_reads, alt_reads, alt_freq, ref_fwd,
                     ref_rev, alt_fwd, alt_rev, bidir]
        return bam_stats

    def add_bam_stats(self, bam_stats, somatic=False):
        """Calculate the bam stats for the variant
        """
        # Add the values to format
        new_format = ["PMCDP", "PMCRD", "PMCAD", "PMCFREQ", "PMCRDF", "PMCRDR",
                      "PMCADF", "PMCADR", "PMCBDIR"]
        if not somatic:
            for name, val in zip(new_format, bam_stats):
                self.format[name] = str(val)
        else:
            for name, val in zip(new_format, bam_stats[0]):
                self.format['normal'][name] = str(val)
            for name, val in zip(new_format, bam_stats[1]):
                self.format['tumor'][name] = str(val)
        return self

    def write(self, somatic=False):
        """Write modified variant line
        """
        if not somatic:
            info_, format_names, format_vals = [], [], []
            for name, val in self.info.items():
                if name == val:
                    info_.append(name)
                else:
                    info_.append('='.join([name, val]))
            for name, val in self.format.items():
                format_names.append(name)
                format_vals.append(val)
            return ('\t'.join([self.chr, self.pos, self.sample_id, 
                               self.ref, self.alt, self.qual, self.filter] + 
                              [';'.join(info_), ':'.join(format_names), 
                               ':'.join(format_vals)]) + '\n')

        else:
            info_, format_names, normal_format_vals, tumor_format_vals =\
                [], [], [], []
            for name, val in self.info.items():
                if name == val:
                    info_.append(name)
                else:
                    info_.append('='.join([name, val]))
            for name, val in self.format['normal'].items():
                format_names.append(name)
                normal_format_vals.append(val)
            for name, val in self.format['tumor'].items():
                tumor_format_vals.append(val)
            return ('\t'.join([self.chr, self.pos, self.sample_id,
                               self.ref, self.alt, self.qual, self.filter] + 
                              [';'.join(info_), ':'.join(format_names), 
                               ':'.join(normal_format_vals), 
                               ':'.join(tumor_format_vals)]) + '\n')

