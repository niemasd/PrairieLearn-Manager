#! /usr/bin/env python3
'''
PrairieLearn Manager (Niema Moshiri 2024)
'''

# standard imports
from json import load as jload
from os.path import isdir
from pathlib import Path
from sys import argv, stderr

# useful constants
VERSION = '0.0.1'
DEFAULT_TITLE = "PrairieLearn Manager v%s" % VERSION
ROOT_PATH = Path('/')

# error message
def error(s, file=stderr, retval=1):
    print("[ERROR] %s" % s, file=file); exit(retval)

# import prompt_toolkit
try:
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.shortcuts import input_dialog, message_dialog, radiolist_dialog
except:
    error("Unable to import 'prompt_toolkit'. Install via: 'pip install prompt_toolkit'")

# app: welcome message
def app_welcome():
    text = HTML("Welcome to <ansiblue>PrairieLearn Manager v%s</ansiblue>!\n\n<ansigreen>Niema Moshiri 2024</ansigreen>" % VERSION)
    message_dialog(title=DEFAULT_TITLE, text=text).run()

# app: navigate to find PrairieLearn course
def app_nav_course(curr_path=Path.cwd(), title=DEFAULT_TITLE, show_hidden=False):
    while True:
        # set things up
        text = HTML("<ansired>Current Path: %s</ansired>" % curr_path)
        values = list()

        # Add "Go to Parent" option if the current path is not the root of the filesystem
        if curr_path != ROOT_PATH:
            values.append((curr_path.parent, HTML("<ansiblue>.. (Parent Folder)</ansiblue>")))

        # Add "Select This Course" if this is a PL course
        if (curr_path / 'infoCourse.json').is_file():
            values.append(('.', HTML("<ansigreen>--- Select This Course ---</ansigreen>")))

        # add all children of this path
        for child in sorted(curr_path.iterdir(), key=lambda x: x.name.lower()):
            if child.is_dir() and (show_hidden or child.name[0] != '.'):
                try:
                    if (child / 'infoCourse.json').is_file():
                        values.append((child, HTML("<ansigreen>%s</ansigreen>" % child.name)))
                    else:
                        values.append((child, child.name))
                except:
                    continue # skip folders we don't have access to

        # run the dialog and handle its return value
        val = radiolist_dialog(title=title, values=values, text=text).run()
        if val is None:
            return None
        elif val == '.':
            return curr_path
        else:
            curr_path = val

# class to represent a PrairieLearn course
class PLCourse:
    # initialize this PLCourse object
    def __init__(self, course_path):
        if not (course_path / 'infoCourse.json').is_file():
            error("Invalid PrairieLearn course path: %s" % course_path)
        self.course_path = course_path

    # run app to manage this course
    def app_manage(self):
        text = '\n'.join('- %s: %s' % tup for tup in sorted(jload(open(self.course_path / 'infoCourse.json')).items(), key=lambda x: x[0]))
        message_dialog(title=str(self.course_path), text=text).run()
        pass # TODO REPLACE WITH ACTUAL APP

# main program logic
def main():
    # parse command line arguments (if applicable)
    if len(argv) > 2 or '-h' in argv or '--help' in argv:
        error("USAGE: %s [path_to_prairielearn_repo]" % argv[0])
    elif len(argv) == 2:
        pl_course_dir = Path(argv[1])
        if not pl_course_dir.is_dir():
            error("Directory not found: %s" % argv[1])
    else:
        pl_course_dir = None # will use app to find PrairieLearn Course later

    # run app
    if pl_course_dir is None:
        app_welcome(); pl_course_dir = app_nav_course()
    pl_course = PLCourse(pl_course_dir)
    pl_course.app_manage()

# run main program
if __name__ == "__main__":
    main()
