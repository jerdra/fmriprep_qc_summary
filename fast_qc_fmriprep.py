#!/usr/bin/env python

'''
Given an fmriprep derivatives directory, build a QC process page to quickly process subjects

Usage:
    fast_qc_fmriprep.py [options] <fmriprep_dir> <output_dir>

Arguments:
    <fmriprep_dir>                          Full path to FMRIPREP derivatives directory
    <output_dir>                            Full path to output directory to dump QC files into

Optional:
    -n, --none                              Placeholder
    -i, --ignore FIELD                      Add BIDS fields to ignore (repeatable)
'''

import os
import bids
from docopt import docopt
import re

def filter_ignored_fields(filelist, ignore_fields):
    '''
    Given a list of BIDS file names (full name not needed, just the substrings of interest),
    remove any unwanted fields

    Returns a set
    '''

    if not ignore_fields:
        return set(filelist)

    #For each field to remove, go through list and remove
    new_list = []
    for i in ignore_fields:

        #Set up regex to look for substring match
        pattern = re.compile("{}-.*?(?=_)".format(i))

        for f in filelist:

            try:
                match = pattern.findall(f)[0]
            except IndexError:
                new_list.append(f)

            new_list.append( f.replace('_{}'.format(match),'') )

    return set(new_list)

def detect_fieldmaps(fmriprep_dir,subjects):
    '''
    Checks if key fieldmaps svg exists within any one subject directory
    '''

    #Loop through subject output directories
    for s in subjects:
        fig_dir = os.path.join(fmriprep_dir,'sub-{}'.format(s),'figures')
        svgs = os.listdir(fig_dir)

        if any([True if 'fmap_mask' in f else False for f in svgs]):
            return True

    #If not a single subject has a fmap_mask svg file, then fmaps don't exist
    return False
    

def participants_tsv(layout,output,ignore_fields):
    '''
    Generate a template for participants.tsv by scraping the output file types
    
    layout                          BIDSLayout object
    output                          Directory to output into
    ignore_fields                   List of fields to ignore when generating the columns of participants.tsv
    '''

    #Get all BOLD files and remove extension
    f = layout.get(extension='nii.gz',space='T1w',suffix='bold')
    f = list(set(['_'.join(x.filename.strip('.nii.gz').split('_')[1:]) for x in f]))
    f = filter_ignored_fields(f,ignore_fields)

    #Check if fmaps exist 
    fmap_exists = detect_fieldmaps(layout.root, layout.get_subjects()) 
    fmap_col = ['fmap_mask'] if fmap_exists else []

    #Make participants.tsv file!
    tsv = os.path.join(output,'participants.tsv')

    #Header line contains subject, anatomical, fmaps, and sorted functional
    header = ['subject'] + ['preproc_T1w'] + fmap_col + [s for s in sorted(list(f))]

    with open(tsv,'w') as f:

        #Write header
        f.write( '\t'.join(header) )
        f.write( '\n' )

    return

def get_broad_qc(sub_figs):
    '''
    Given a list of niftis belonging to a particular subject pull out:
        -   anatomical
        -   fieldmap if exists

    SVG files
    '''

    #Pull out anatomical svg (brainmask, mni)
    brainmask = [s for s in sub_figs if '_seg_brainmask' in s]
    mni = [s for s in sub_figs if 't1_2_mni' in s]

    #Pull out fieldmap magnitude mask
    try:
        mag = [s for s in sub_figs if 'fmap_mask' in s]
        mag_desc = ['magnitude mask']
    except IndexError:
        mag = []
        mag_desc = []


    desc = ['brainmask','t12mni'] + mag_desc
    return (brainmask + mni + mag, desc)

def get_svg_markup(svg):
    '''
    Given the full path to an svg and a basepath
    Generate an HTML snippet that inserts an svg image
    '''

    template = '''
    <tr><td><object type="image/svg+xml" data="{}"></object></td></tr>
    '''
    return template.format(svg)

def make_broad_html(sub, sub_figs, sub_files, output, fig_dir):
    '''
    Generate HTML code for broad QC (exclusion here should invalidate all scans)
    '''

    html = []
    html += ['{}\n'.format('sub-'+sub)]

    svgs,desc = get_broad_qc(sub_figs)
    svgs = [os.path.join(fig_dir,s) for s in svgs]

    desc_markup = ['<tr><td>{}</td></tr>'.format(d) for d in desc]
    html += [d + get_svg_markup(os.path.relpath(f,output)) for f,d in zip(svgs,desc)]



    return html

def get_task_ordering_key(bidsfile):
    '''
    Given a task-associated BIDSFile object, return a tuple which determines the ordering of the file
    '''

    entities = bidsfile.entities

    task = entities['task']
    run = entities['run'] if 'run' in entities else '1'

    return (task,run)

def make_task_html(sub,output,fig_dir,sub_figs,task_file):
    '''
    Generate HTML code for taskfile QC
    '''
    
    #Step 1: Write the task name into the html
    html = []
    html += [task_file.filename]

    #Step 2: Find the associated SVGs
    # 1: If FMAP exists then MAG --> EPI
    # 2: SDC
    # 3: EPI --> T1 

    #Get BIDS base specification
    pattern = re.compile('.*?(?=_space)')
    try:
        bidsbase = pattern.findall(task_file.filename)[0]
    except IndexError:
        return

    #With this we can now filter the sub_figs to those of interest
    task_figs = [f for f in sub_figs if bidsbase in f]

    #Pull fmap if available and add to HTML
    try:
        fmap_svg = [s for s in task_figs if 'fmap_reg.svg' in s][0]
    except IndexError:
        pass
    else:
        fmap_svg = os.path.relpath(os.path.join(fig_dir,fmap_svg), output)
        html += [get_svg_markup(fmap_svg)]

    #Now do SDC if available
    try:
        sdc_svg = [s for s in task_figs if 'sdc' in s][0]
    except IndexError:
        pass
    else:
        sdc_svg = os.path.relpath(os.path.join(fig_dir,sdc_svg), output)
        html += [get_svg_markup(sdc_svg)]

    #Finally do epi-->T1
    try:
        epi2t1_svg = [s for s in task_figs if ('bbregister' in s) or ('coreg' in s)][0]
    except IndexError:
        pass
    else:
        epi2t1_svg = os.path.relpath(os.path.join(fig_dir,epi2t1_svg), output)
        html += [get_svg_markup(epi2t1_svg)]

    return [bidsbase + '.html', html]

def add_link(pg,text):
    '''
    Return markup for adding a page
    '''

    return '<td><a href="./{}">{}</a></td>'.format(pg,text)


def main():

    args = docopt(__doc__)

    fmriprep_dir    =   args['<fmriprep_dir>']
    output_dir      =   args['<output_dir>']
    ignore_fields   =   args['--ignore']

    layout = bids.BIDSLayout(fmriprep_dir,derivatives=True,validate=False)

    # Generate participants.tsv template
    participants_tsv(layout,output_dir,ignore_fields)

    #Now loop through each participant's scans and start building QC pages
    html_series = []
    subjects = layout.get_subjects()
    for ind,s in enumerate(subjects):

        broad_name = '{}_sub-{}.html'.format(ind,s)

        #Get relevant files for subject
        fig_dir = os.path.join(layout.root,'sub-{}'.format(s),'figures')
        sub_figs = os.listdir(fig_dir)
        sub_files = layout.get(subject=s,extension='nii.gz')

        #Get broad QC markup
        broad_html = make_broad_html(s, sub_figs, sub_files, output_dir, fig_dir)

        #Link broad HTML to previous subject's last taskfile
        if ind > 0:
            broad_html += [add_link(task_htmls[-1][0],'Previous Page')]

        #Get functional markup (one per taskfile)
        task_files = layout.get(subject=s,extension='nii.gz',suffix='bold',space='T1w')
        task_files = sorted(task_files,key = lambda x: get_task_ordering_key(x))
        task_htmls = [make_task_html(s,output_dir,fig_dir,sub_figs,t) for t in task_files]

        #Step 1: Write the first task_html name into broad_html
        try:
            broad_html += [add_link(task_htmls[0][0], 'Next Page')]
        except IndexError:
            import pdb; pdb.set_trace()

        #Step 2: Link broad html to first task_html
        task_htmls[0][1] += [add_link(broad_name,'Previous Page')]

        #Step 3: Link each task HTML to the previous
        for i in range(1,len(task_htmls)):
            task_htmls[i][1] += [add_link(task_htmls[i-1][0], 'Previous Page')]

        #Step 4: Link each task HTML to the next
        for i in range(0,len(task_htmls) - 1):
            task_htmls[i][1] += [add_link(task_htmls[i+1][0], 'Next Page')]

        #Step 5: Link broad_html to the next subject
        if ind != len(subjects) - 1:
            broad_html += [add_link('{}_sub-{}.html'.format(ind+1,subjects[ind+1]),'Next Subject')]
            task_htmls[-1][1] += [add_link('{}_sub-{}.html'.format(ind+1,subjects[ind+1]),'Next Page')]


        #Write out files
        with open(os.path.join(output_dir,broad_name),'w') as f:
            f.writelines(broad_html)

        #Write out task files
        for t in task_htmls:
            with open(os.path.join(output_dir,t[0]),'w') as f:
                f.writelines(t[1])


if __name__ == '__main__':
    main()
