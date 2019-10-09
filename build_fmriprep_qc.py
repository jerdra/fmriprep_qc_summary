#!/usr/bin/env python

'''
Given the fmriprep derivatives directory, build a paginated QC page 

Usage:
    build_fmriprep_qc.py [-i FIELD]... <fmriprep_dir> <output_dir>

Arguments:
    <fmriprep_dir>                          Full path to FMRIPREP derivatives directory
    <output_dir>                            Full path to output directory to dump QC files into

Optional:
    -i, --ignore FIELD                      BIDS field to toss out when categorize scan types
    -s, --space SPACE                       Search for a particular space [Default: T1w]
'''


import os
import bids
from docopt import docopt
import re


FIGSPERPAGE=20

def filter_ignored_fields(filelist, ignore_fields):
    '''
    Given a list of BIDS file names (full name not needed, just the substrings of interest),
    remove any unwanted fields

    Returns a set
    '''

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

    #Filter out anything in fields to be ignored

    #Get T1w preprocessed anatomical files and remove extension
    a = [x for x in layout.get(extension='nii.gz',suffix='T1w')
            if x.filename.split('_')[1] == 'T1w.nii.gz']
    a = set(['_'.join(x.filename.strip('.nii.gz').split('_')[1:]) for x in a])

    #Next generate the unique list of descriptors for BOLD and anatomical
    descriptors = ['_'.join(x.filename.strip('.')

    pass

def add_image_row(tag,svg):
    '''
    Insert HTML markup for inserting image with tag
    '''

    return ''' 
    <tr><td>{}</td></tr> 
    <tr><td><object type="image/svg+xml" data="{}"></object></td></tr>
    '''.format(tag,svg)

def gen_anatomical_qc(root_dir,subjects,keyword,output):
    '''
    Given a root directory, subjects, a keyword and output filename
    Make an anatomical QC page
    '''

    html = []
    missing_svg = []
    page_num = 0
    for i,s in enumerate(subjects):

        figdir = os.path.join(root_dir,'sub-' + s, 'figures')
        svgs = os.listdir(figdir)

        #Search for relevant SVG
        try:
            svg = [f for f in svgs if keyword in f][0]
        except IndexError:
            missing_svg.append(s)
            continue

        #Now build paginated QC page, link to next one if available
        if ((i != 0) and (i % FIGSPERPAGE == 0)) or (i == len(subjects)-1):

            page = os.path.join(output,'{}.html'.format(page_num))

            #Handle previous and next page
            prev_pg = ''
            nxt_pg = ''

            #If a page can still be fit, then add next page button
            if i + FIGSPERPAGE <= len(subjects):
                nxt_pg = '<td><a href="./{}.html">Next Page</a></td>'.format(page_num+1)

            #If at least one page is already done, then add a previous page button
            if i - FIGSPERPAGE > 0:
                prev_pg = '<td><a href="./{}.html">Previous Page</a></td>'.format(page_num-1)
            footer = '<tr>{}{}</tr>'.format(prev_pg,nxt_pg)
            html.append(footer)

            #Write, increment page
            with open(page,'w') as f:
                f.writelines(html)
            html = []
            page_num += 1

        #Get full path to SVG file, make relative to page
        svg = os.path.join(figdir,svg)
        rel_svg = os.path.relpath(svg, output)

        #Append to HTML
        html.append(add_image_row(s, rel_svg))

    return

def make_anatomical_qc(layout,output):
    '''
    Make brainmask and t1 --> MNI QC pages
    '''

    #Get list of subjects and fmriprep dir
    fmriprep_dir = layout.root
    subjects = [s for s in layout.get_subjects() if 
            os.path.exists(os.path.join(fmriprep_dir,'sub-'+s,'figures'))]

    #Brainmask
    brainmask_dir = os.path.join(output,'brainmask')
    makedir(brainmask_dir)
    gen_anatomical_qc(fmriprep_dir,subjects,'_seg_brainmask',brainmask_dir)

    #T12MNI
    t12mni_dir = os.path.join(output,'t12mni')
    makedir(t12mni_dir)
    gen_anatomical_qc(fmriprep_dir,subjects,'t1_2_mni',t12mni_dir)

def makedir(path):
    try:
        os.makedirs(path,exist_ok=True)
    except OSError:
        pass
    return

def get_func_svg(sub,ses,task,run,figtype,flist):
    '''
    Pull svg for specific task, run and figure type from a list of figures in fmriprep derivatives
    '''

    for f in flist:
        splitted = f.split('.')[0].split('_')


        #Checks
        sub_in = ('sub-'+sub) in splitted
        ses_in = ('ses-'+str(ses)) in splitted
        task_in = ('task-'+task) in splitted

        if run:
            run_in = (('run-'+str(run)) in splitted) or (('run-0'+str(run)) in splitted)
        else:
            run_in = True

        figtype_in = figtype in splitted

        if sub_in and ses_in and task_in and run_in and figtype_in:
            return f

def make_fc_html(svg_tups, output):
    '''
    Given a list of tuples mapping task files names to their svg counterparts,
    construct an html file
    '''
    html = []
    page_num = 0
    
    for i,t in enumerate(svg_tups):

        #Split tup to filename tag and svg
        filename,svg = t

        #Now build paginated QC page, link to next one if available
        if ((i != 0) and (i % FIGSPERPAGE == 0)) or (i == len(svg_tups)-1):

            page = os.path.join(output,'{}.html'.format(page_num))

            #Handle previous and next page
            prev_pg = ''
            nxt_pg = ''

            #If a page can still be fit, then add next page button
            if i + FIGSPERPAGE <= len(svg_tups):
                nxt_pg = '<td><a href="./{}.html">Next Page</a></td>'.format(page_num+1)

            #If at least one page is already done, then add a previous page button
            if i - FIGSPERPAGE > 0:
                prev_pg = '<td><a href="./{}.html">Previous Page</a></td>'.format(page_num-1)
            footer = '<tr>{}{}</tr>'.format(prev_pg,nxt_pg)
            html.append(footer)

            #Write, increment page
            with open(page,'w') as f:
                f.writelines(html)
            html = []
            page_num += 1

        #Get full path to SVG file, make relative to page
        rel_svg = os.path.relpath(svg, output)

        #Append to HTML
        html.append(add_image_row(filename, rel_svg))

    return

def gen_functional_qc(root_dir,taskfiles,task,keywords,output):
    '''
    Given the fmriprep derivatives root dir, subjects, task and keywords
    Generate html qc pages in a hierarchical structure
    '''

    missing_svg = []
    map_tuples = []

    for f in taskfiles:

        sub = f.entities['subject']
        ses = f.entities['session']

        try:
            run = f.entities['run']
        except KeyError:
            run = False

        figdir = os.path.join(root_dir,'sub-' + sub, 'figures')
        svgs = os.listdir(figdir)

        try:
            svg = [get_func_svg(sub,ses,task,run,k,svgs) for k in keywords][0]
        except IndexError:
            missing_svg.append(f)
            continue

        map_tuples.append( (f.filename, os.path.join(figdir,svg)) )

    make_fc_html(map_tuples, output)

def make_functional_qc(layout,output, space):
    '''
    For each task make each QC modality
    '''

    #For each task there are 3 modalities to make
    fmriprep_dir = layout.root
    subjects = [s for s in layout.get_subjects() if
            os.path.exists(os.path.join(fmriprep_dir,'sub-'+s,'figures'))]
    
    for t in layout.get_tasks():

        taskfiles = layout.get(task=t,suffix='bold',space=space,extension='.nii.gz')

        #EPI-TO-T1
        epi2t1_dir = os.path.join(output,t,'epi2t1')
        makedir(epi2t1_dir)
        gen_functional_qc(fmriprep_dir,taskfiles,t,['bbregister','coreg'],epi2t1_dir)

        #SDC
        sdc_dir = os.path.join(output,t,'sdc')
        makedir(sdc_dir)
        gen_functional_qc(fmriprep_dir,taskfiles,t,['sdc'],sdc_dir)

        #ROIS
        roi_dir = os.path.join(output,t,'rois')
        makedir(roi_dir)
        gen_functional_qc(fmriprep_dir,taskfiles,t,['rois'],roi_dir)

    return

def main():

    args    =   docopt(__doc__)
    fmriprep_dir    =   args['<fmriprep_dir>']
    output_dir      =   args['<output_dir>']
    ignore_fields   =   args['--ignore']
    space           =   args['--space']


    layout = bids.BIDSLayout(fmriprep_dir,derivatives=True,validate=False)

    #Generate participants.tsv template
    participants_tsv(layout,output_dir,space,ignore_fields)

    #Make anatomical QC pages
    anat_qc = os.path.join(output_dir,'anat')
    makedir(anat_qc)
    make_anatomical_qc(layout, anat_qc)

    #Make functional QC pages
    func_qc = os.path.join(output_dir,'func')
    makedir(func_qc)
    make_functional_qc(layout,func_qc, space)


if __name__ == '__main__':
    main()
