#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Time-stamp: <2014-10-31 20:08:00 vk>

import os
import sys
import re
import logging
from optparse import OptionParser
from datetime import datetime
import shutil
import fnmatch ## for searching matching directories

## TODO:
## * fix parts marked with «FIXXME»
## * document "no target folder given" with askfordir (just like no askfordir)

PROG_VERSION_NUMBER = u"0.3"
PROG_VERSION_DATE = u"2013-09-14"

## better performance if ReEx is pre-compiled:

## search for: «YYYY-MM-DD»
DATESTAMP_REGEX = re.compile("\d\d\d\d-[01]\d-[0123]\d")
DEFAULT_ARCHIVE_PATH = os.path.join(os.path.expanduser("~"), "archive", "events_memories")
PAUSEONEXITTEXT = "    press <Enter> to quit"

USAGE = u"""
    {0} <options> <file(s)>

This script moves items (files or directories) containing ISO datestamps
like "YYYY-MM-DD" into a directory stucture for the corresponding year.

You define the base directory either in this script (or using the
command line argument "--archivedir"). The convention is e.g.:

        <archivepath>/2009
        <archivepath>/2010
        <archivepath>/2011

Per default, this script extracts the year from the datestamp of
each file and moves it into the corresponding directory for its year:

     {0} 2010-01-01_Jan2010.txt 2011-02-02_Feb2011.txt
... moves "2010-01-01_Jan2010.txt" to "<archivepath>/2010/"
... moves "2011-02-02_Feb2011.txt" to "<archivepath>/2011/"

OPTIONALLY you can define a sub-directory name with option "-d DIR". If it
contains no datestamp by itself, a datestamp from the first file of the
argument list will be used. This datestamp will be put in front of the name:

     {0}  -d "2009-02-15 bar"  one two three
... moves all items to: "<archivepath>/2009/2009-02-15 bar/"

     {0}  -d bar  2011-10-10_one 2008-01-02_two 2011-10-12_three
... moves all items to: "<archivepath>/2011/2011-10-10 bar/"

If you feel uncomfortable you can simulate the behavior using the "--dryrun"
option. You see what would happen without changing anything at all.


:copyright: (c) 2011 and later by Karl Voit <tools@Karl-Voit.at>
:license: GPL v2 or any later version
:bugreports: <tools@Karl-Voit.at>
:version: {1} from {2}\n""".format(sys.argv[0], PROG_VERSION_NUMBER, PROG_VERSION_DATE)

parser = OptionParser(usage=USAGE)

parser.add_option("-d", "--directory", dest="targetdir",
                  help="name of a target directory that should be created (optionally add datestamp)", metavar="DIR")

parser.add_option("--askfordirectory", dest="askfordir", action="store_true",
                  help='similar to "-d" but tool asks for an input line when invoked. ' +\
                  'Shortcut: "rp" moves to folder named "Rohpanorama".')

parser.add_option("-a", "--append", dest="append", action="store_true",
                  help="if target directory already exists, append to it " +
                       "instead of aborting.")

parser.add_option("--archivepath", dest="archivepath",
                  help='overwrite the default archive base directory which contains one '
                       'subdirectory per year. DEFAULT is currently "%s" (which can be modified '
                       'in "%s")' % (DEFAULT_ARCHIVE_PATH, sys.argv[0]), metavar="DIR")

## parser.add_option("-b", "--batch", dest="batchmode", action="store_true",
##                   help="Do not ask for user interaction (at the end of the process)")

parser.add_option("--dryrun", dest="dryrun", action="store_true",
                  help="Does not make any changes to the file system. Useful for testing behavior.")

parser.add_option("--pauseonexit", dest="pauseonexit", action="store_true",
                  help="Asks for pressing the Enter key on any exit.")

parser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                  help="enable verbose mode")

parser.add_option("--version", dest="version", action="store_true",
                  help="display version and exit")

(options, args) = parser.parse_args()

global user_selected_suggested_directory
user_selected_suggested_directory = False



def handle_logging():
    """Log handling and configuration"""

    if options.verbose:
        FORMAT = "%(levelname)-8s %(asctime)-15s %(message)s"
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    else:
        FORMAT = "%(levelname)-8s %(message)s"
        logging.basicConfig(level=logging.INFO, format=FORMAT)


def error_exit(errorcode, text):
    """exits with return value of errorcode and prints to stderr"""

    sys.stdout.flush()
    logging.error(text)

    if options.dryrun or options.pauseonexit:
        raw_input(PAUSEONEXITTEXT)

    sys.exit(errorcode)


def extract_date(text):
    """extracts the date from a text. Returns a datetime-object if a valid date was found, otherwise returns None."""

    components = re.search(DATESTAMP_REGEX, os.path.basename(text.strip()))
    try:
        return datetime.strptime(components.group(), "%Y-%m-%d")
    except (ValueError, AttributeError):
        return None


def extract_targetdirbasename_with_datestamp(targetdirbasename, args):
    """extracts the full targetdirname including ISO datestamp"""

    current_datestamp = extract_date(targetdirbasename)
    if current_datestamp:
        logging.debug('targetdir "%s" contains datestamp. Extracting nothing.' % targetdirbasename)
        return targetdirbasename
    else:
        first_datestamp = None
        logging.debug('targetdir "' + targetdirbasename + '" contains no datestamp. '
                      'Trying to extract one from the arguments ...')
        for item in args:
            itembasename = os.path.basename(item.strip())
            current_datestamp = extract_date(itembasename)
            if current_datestamp:
                logging.debug('found datestamp "%s" in item "%s"' % (current_datestamp.isoformat()[:10], item.strip()))
                if first_datestamp:
                    logging.debug('comparing current datestamp "%s" with first datestamp' % current_datestamp.isoformat()[:10])
                    if current_datestamp != first_datestamp:
                        logging.warning('Datestamp of item "%s" differs from previously found datestamp "%s". '
                                        'Taking previously found.' % (item.strip(), first_datestamp.isoformat()[:10]))
                    else:
                        logging.debug("current datestamp is the same as the first one")
                else:
                    logging.debug('setting first datestamp to "%s"' % current_datestamp.isoformat()[:10])
                    first_datestamp = current_datestamp
            else:
                logging.warning('item "%s" has got no datestamp!' % item.strip())

        if first_datestamp:
            final_targetdir = first_datestamp.isoformat()[:10] + " " + targetdirbasename
            logging.debug('proposed targetdir "%s"' % final_targetdir)
            return final_targetdir
        else:
            error_exit(2, "could not generate any targetdir containing datestamp. Exiting.")

    error_exit(9, "should not reach this line! internal error.")


def assert_each_item_has_datestamp(items):
    """make sure that each item has a valid datestamp"""

    logging.debug("checking each item for valid datestamp")
    for item in items:
        components = re.search(DATESTAMP_REGEX, os.path.basename(item.strip()))
        try:
            item_date = datetime.strptime(components.group(), "%Y-%m-%d")
            return item_date.year
        except (ValueError, AttributeError):
            error_exit(3, 'item "%s" has got no valid datestamp! Can not process this item.' % item)


def make_sure_targetdir_exists(archivepath, targetdir):
    """create directory if necessary; abort if existing and no append options given"""

    logging.debug("make_sure_target_exists: archivepath [%s] targetdir [%s]" % (archivepath, targetdir))
    year = get_year_from_itemname(targetdir)
    complete_target_path = os.path.join(str(archivepath), str(year), str(targetdir))
    global user_selected_suggested_directory
    
    if os.path.isdir(complete_target_path):
        if options.append or user_selected_suggested_directory:
            logging.debug("target directory already exists. Appending files...")
        else:
            error_exit(4, "target directory already exists. Aborting.")
    else:
        if not options.dryrun:
            logging.info('creating target directory: "%s"' % complete_target_path)
            os.mkdir(complete_target_path)
        else:
            logging.info('creating target directory: "%s"' % complete_target_path)

    return complete_target_path


def make_sure_subdir_exists(currentdir, subdir):
    """create directory if necessary; abort if existing and no append options given"""

    logging.debug("make_sure_subdir_exists: currentdir [%s] subdir [%s]" % (currentdir, subdir))
    complete_target_path = os.path.join(currentdir, subdir)

    if os.path.isdir(complete_target_path):
        logging.debug("target directory already exists. Appending files...")
    else:
        if not options.dryrun:
            logging.info('creating directory: "%s"' % complete_target_path)
            os.mkdir(complete_target_path)
        else:
            logging.info('creating directory: "%s"' % complete_target_path)

    return complete_target_path


def get_year_from_itemname(itemname):
    """extract year from item string"""

    ## assert: main() makes sure that each item has datestamp!
    components = re.search(DATESTAMP_REGEX, os.path.basename(itemname))
    try:
        return datetime.strptime(components.group(), "%Y-%m-%d").year
    except (ValueError, AttributeError):
        error_exit(7, 'item "%s" should have a valid datestamp in it. '
                      'Should have been checked before, internal error :-(' % str(itemname))


def move_item(item, destination):
    """move an item to the destination directory"""

    if options.dryrun:
        print 'moving: "%s"  -->   "%s"' % (item, destination)
    elif os.path.isdir(destination):
        try:
            print 'moving: "%s"  -->   "%s"' % (item, destination)
            shutil.move(item, destination)
        except IOError, detail:
            error_exit(5, 'Cannot move "%s" to "%s". Aborting.\n%s' % (item, destination, detail))
    else:
        error_exit(6, 'Destination directory "%s" does not exist! Aborting.' % destination)


def handle_item(itemname, archivepath, targetdir):
    """handles one item and moves it to targetdir"""

    logging.debug("--------------------------------------------")
    logging.debug('processing item "%s"' % itemname)
    logging.debug("with archivepath[%s]  and  targetdir[%s]" % (archivepath, targetdir))

    if not os.path.exists(itemname):
        logging.error('item "%s" does not exist! Ignoring.' % itemname)
    elif targetdir and (options.targetdir or options.askfordir):
        ## targetdir option is given and this directory is created before
        ## so just move items here:
        move_item(itemname, targetdir)
    else:
        ## find the correct <YYYY> subdirectory for each item:
        year = get_year_from_itemname(itemname)
        logging.debug('extracted year "%d" from item "%s"' % (year, itemname))
        destination = os.path.join(archivepath, str(year))
        move_item(itemname, destination)


def generate_absolute_target_dir(targetdir, args, archivepath):
    """returns existing target directory containing a datestamp"""

    logging.debug("trying to find a target dir with datestamp")
    targetdirname = extract_targetdirbasename_with_datestamp(targetdir, args)
    logging.debug('extract_targetdirbasename... returned "%s"' % targetdirname)
    return make_sure_targetdir_exists(archivepath, targetdirname)


def get_potential_target_directories(args, archivepath):
    """takes first argument, extracts its date-stamp, looks for existing
    directories starting with the time-stamp (or similar) and returns the
    list of the directories."""

    firstfile=args[0]
    assert(os.path.exists(firstfile))
    firstfile = os.path.basename(firstfile)
    assert_each_item_has_datestamp([firstfile])

    item_date = extract_date(firstfile)
    yearfolder = os.path.join(archivepath, str(item_date.year))
    assert(os.path.exists(yearfolder))

    ## existing yearfolder found; looking for matching subfolders:
    logging.debug("looking for potential existing target folders for file \"%s\" in folder \"%s\"" % (firstfile, yearfolder))
    datestamp = firstfile[0:10]
    pattern = datestamp+'*'
    directory_suggestions = []
 
    for root, dirs, files in os.walk(yearfolder):
        for directory in fnmatch.filter(dirs, pattern):
            #print( os.path.join(root, filename))
            logging.debug("found matching folder \"%s\"" % (directory))
            directory_suggestions.append(directory)
    logging.debug("found %i potential directory suggestions" % (len(directory_suggestions)))

    return directory_suggestions


def print_potential_target_directories(directory_suggestions):
    """prints list of potential target directories with their shortcuts."""

    number_of_suggestions = len(directory_suggestions)
    assert(number_of_suggestions>0)

    if number_of_suggestions > 1:
        print '\n ' + str(number_of_suggestions) + \
            ' matching target directories found. Enter its number if you want to use one of it:'
    else:
        print '\n One matching target directory found. Enter "1" if you want to use it:'
    
    index = 1 # caution: for usability purposes, we do not start with 0 here!
    for directory in directory_suggestions:
        print '  [' + str(index) + ']  ' + directory
        index += 1
    print '\n'

    return


def is_an_integer(data):
    """returns true if string is an integer"""
    try: 
        int(data)
        return True
    except ValueError:
        return False

    
def main():
    """Main function"""

    if options.version:
        print "%s version %s from %s" % (os.path.basename(sys.argv[0]), PROG_VERSION_NUMBER, PROG_VERSION_DATE)
        sys.exit(0)

    handle_logging()
    logging.debug("options: " + str(options))
    logging.debug("args: " + str(args))

    if options.dryrun:
        logging.info('Option "--dryrun" found, running a simulation, not modifying anything on file system:')

    if options.append and not options.targetdir:
        logging.warning('The "--append" options is only necessary in combination '
                        'with the "--directory" option. Ignoring this time.')

    if options.targetdir and options.askfordir:
        error_exit(8, 'Options "--directory" and "--askfordirectory" are mutual exclusive: '
                      'use one at maximum.')

    archivepath = None
    if options.archivepath:
        logging.debug('overwriting default archive dir with: "%s"' % options.archivepath)
        archivepath = options.archivepath
    else:
        archivepath = DEFAULT_ARCHIVE_PATH

    if not os.path.isdir(archivepath):
        error_exit(1, '\n\nThe archive directory "%s" is not a directory!\n'
                      'modify default setting in "%s" or provide a valid '
                      'directory with command line option "--archivepath".\n' % (archivepath, sys.argv[0]))

    if len(args) < 1:
        parser.error("Please add at least one file name as argument")

    targetdirname = None
    if options.targetdir:
        targetdirname = generate_absolute_target_dir(options.targetdir, args, archivepath)
    elif options.askfordir:
        
        directory_suggestions = get_potential_target_directories(args, archivepath)
        number_of_suggestions = len(directory_suggestions)
        if number_of_suggestions > 0:
            print_potential_target_directories(directory_suggestions)
        
        print "Please enter directory basename: "
        targetdirname = sys.stdin.readline().strip()
        if (not targetdirname):
            ## if no folder is given by the user, act like askfordir is not the case:
            logging.debug("targetdirname was empty: acting, like --askfordir is not given")
            assert_each_item_has_datestamp(args)
        else:
            
            if targetdirname == 'lp':
                ## overriding targetdir with lp-shortcut:
                logging.debug("targetdir-shortcut 'lp' (low prio) found")
                targetdirname = make_sure_subdir_exists(os.getcwd(), 'lp')
                
            elif targetdirname == 'rp':
                ## overriding targetdir with rp-shortcut:
                logging.debug("targetdir-shortcut 'rp' (Rohpanorama) found")
                targetdirname = make_sure_subdir_exists(os.getcwd(), 'Rohpanoramas')
                
            elif number_of_suggestions > 0 and is_an_integer(targetdirname):
                ## special shortcut: numbers within number_of_suggestions are for suggested directories
                targetdirint = int(targetdirname)
                if targetdirint <= number_of_suggestions and targetdirint > 0:
                    global user_selected_suggested_directory
                    user_selected_suggested_directory = True
                    targetdirname = directory_suggestions[targetdirint - 1] # -1 fixes that we start from 1 instead of 0
                    targetdirname = generate_absolute_target_dir(targetdirname, args, archivepath)
                    logging.debug("user selected existing directory \"%s\"" % (targetdirname))
                else:
                    ## if number is not in range of suggestions, use it as folder name like below:
                    targetdirname = generate_absolute_target_dir(targetdirname, args, archivepath)

            else:
                targetdirname = generate_absolute_target_dir(targetdirname, args, archivepath)
    else:
        assert_each_item_has_datestamp(args)

    if targetdirname:
        logging.debug('using targetdirname "%s"' % targetdirname)
    else:
        logging.debug("using no targetdir, sorting each item into %s/<YYYY>" % archivepath)

    print '\n' ## make it more sexy
    for itemname in args:
        handle_item(itemname.strip(), archivepath, targetdirname)

    logging.debug("successfully processed all items.")

    if options.dryrun or options.pauseonexit:
        raw_input(PAUSEONEXITTEXT)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:

        logging.info("Received KeyboardInterrupt")

## END OF FILE #################################################################

#end
