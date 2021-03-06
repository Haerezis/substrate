#!/usr/bin/python

#This script use the substrate program to optimize .scop files for each
#profile type independently (mono criteria) and for different minimal aggregating rates.
#The aggregation strategy used is the default one.
#
#It also compare the original .scop file to the generated ones to see if some
#statements were aggregated or not. It then produce a gnuplot data file with the results.

import os, os.path, glob, re
from sys import argv
from subprocess import call

###GLOBAL VARIABLES
#We will try to benchmark for rate from rate_begin to rate_end
#with a increment of rate_int
rate_begin=0.0
rate_end=1.0
rate_inc=0.1

#The path of the different directory/binary needed (should be given
#as the program argument).
substrate_bin="."
scops_dir="."
aggr_scops_dir="."

#Gnuplot command printed in the data file (to be able to directly
#plot the data
gnuplot_commands = "#Gnuplot datafile"

#Gnuplot comment printed before the data, explaining the format
gnuplot_format = """\
# Format : min_rate_for_aggregation nb_aggregated_statement_TYPE.... nb_statement_original_scop
# with TYPE being 'reuse', 'parallelism', 'vectorization' etc..."""


def print_usage() :
    print "Usage : {0} <substrate_path> <scops_directory | scop_filepath> <aggregated_scops_directory> <results_directory> [-no-substrate] [-no-gnuplot]"\
            .format(argv[0])


#The profile type option used to call substrate in monocriteria mode.
#The script will try to call benchmark substrate for each of these profile type
profile_options = {
        "reuse" : "--reuse-weight",
        "parallelism" : "--paral-weight",
        "vectorization" : "--vector-weight",
        "tiling_hyperplane" : "--tiling-weight" }

#Optimize in monocriteria for every profile type in the list, for every minimal rate
#in the list for every scop file in the list.
def substrate(profile_type_list , rate_list, scop_filename_list) :
    for profile_type in profile_type_list :
        directory = "{0}/{1}".format(aggr_scops_dir,profile_type)
        if not os.path.exists(directory) :
            os.makedirs(directory)

        for rate in rate_list :
            directory_rate = "{0}/{1}".format(directory,rate)
            if not os.path.exists(directory_rate) :
                os.makedirs(directory_rate)

            for scop_filename in scop_filename_list :
                command = [substrate_bin,
                        "-o",
                        "{0}/{1}".format(directory_rate,scop_filename),
                        "--min-rate",
                        str(rate),
                        profile_options[profile_type],
                        "1.0",
                        "{0}/{1}".format(scops_dir,scop_filename)]
                #print command
                call( command )
#Get the number of statement in a .scop file.
def nb_stmt_in_scop_file(scop_filepath) :
    with open(scop_filepath, "r") as scop :
        for line in scop :
            if re.search("# Number of statements",line) :
                line = scop.next()
                return int(line)
    return 0

#Generate the gnuplot data files for every optimized scop.
def gnuplot_data(profile_type_list, rate_list, scop_filename_list) :

    for scop_filename in scop_filename_list :
        results = {key: [] for key in ["rate"]+profile_type_list+["nb_stmt_original"]}
        for rate in rate_list :
            results["rate"].append(rate)
            nb_stmt_original = nb_stmt_in_scop_file("{0}/{1}".format(scops_dir,scop_filename))
            results["nb_stmt_original"].append(nb_stmt_original)
            for profile_type in profile_type_list :
                directory = "{0}/{1}/{2}".format(aggr_scops_dir,profile_type,rate)
                nb_stmt = nb_stmt_in_scop_file("{0}/{1}".format(directory,scop_filename))
                results[profile_type].append(nb_stmt_original - nb_stmt)
        #write result in file
        res_filepath = "{0}/{1}.results".format(res_dir, scop_filename)
        with open (res_filepath, "w") as res_file :
            res_file.write(gnuplot_commands+"\n\n")
            res_file.write(gnuplot_format+'\n')
            
            rate_list = results["rate"]
            del results["rate"]
            nb_stmt_original_list = results["nb_stmt_original"]
            del results["nb_stmt_original"]

            res_file.write("#")
            res_file.write("rate")
            res_file.write(" \tnb_stmt_original")
            for k in sorted(results) : res_file.write(" \t"+k)
            res_file.write('\n')
            for idx,rate in enumerate(rate_list) :
                res_file.write(" "+str(rate))
                res_file.write(" \t"+str(nb_stmt_original_list[idx]))
                for key in sorted(results) :
                    res_file.write(" \t" + str(results[key][idx]))
                res_file.write('\n')

                



# Check if there is enough argument
if len(argv) < 5 :
    print "ERROR : Not enough arguments."
    print_usage()
    exit(1)

substrate_bin=argv[1]
scops_dir=argv[2]
aggr_scops_dir=argv[3]
res_dir=argv[4]

if not os.path.isfile(argv[1]) :
    print "ERROR : substrate program \"{0}\" doesn't exists.".format(substrate_bin)
    print_usage()
    exit(1)

# Check if the directories given as arguments are directories and exists.
if not ( os.path.isdir(scops_dir) or os.path.isfile(scops_dir) ) :
    print "ERROR : \"{0}\" is not a directory or doesn't exists.".format(scops_dir)
    print_usage()
    exit(1)
if not os.path.isdir(aggr_scops_dir) :
    print "ERROR : \"{0}\" is not a directory or doesn't exists.".format(aggr_scops_dir)
    print_usage()
    exit(1)
if not os.path.isdir(res_dir) :
    print "ERROR : \"{0}\" is not a directory or doesn't exists.".format(res_dir)
    print_usage()
    exit(1)


# Creating aggregated scops
if os.path.isdir(scops_dir) :
    original_working_directory = os.getcwd()
    os.chdir(scops_dir)
    scops_list = glob.glob("*.scop")
    os.chdir(original_working_directory)
else :
    tmp = os.path.split(scops_dir)
    scops_dir = tmp[0]
    scops_list = [tmp[1]]

# Creating the list of rate that will be computed
rate = rate_begin
rate_list = []
while rate <= rate_end :
    rate_str = ('%.5f' % (rate)).rstrip('0')
    if rate_str.endswith('.') : rate_str = rate_str + '0'
    rate_list.append(rate_str)
    rate = rate+rate_inc

# List of the profile type we're asking to benchmark
profile_type_list = profile_options.keys()
if "-no-substrate" not in argv :
    substrate(profile_type_list, rate_list, scops_list)
if "-no-gnuplot" not in argv :
    gnuplot_data(profile_type_list, rate_list, scops_list)
