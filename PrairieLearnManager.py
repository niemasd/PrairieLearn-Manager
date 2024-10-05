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

# useful prompt_toolkit constants
APP_EXIT_TUPLE = (False, HTML('<ansired>--- Exit Application ---</ansired>'))

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
        for child in sorted(curr_path.iterdir(), key=lambda x: x.name.strip().lower()):
            if child.is_dir() and (show_hidden or child.name[0] != '.'):
                try:
                    if (child / 'infoCourse.json').is_file():
                        values.append((child, HTML("<ansigreen>%s</ansigreen>" % child.name)))
                    else:
                        values.append((child, child.name))
                except:
                    continue # skip folders we don't have access to

        # add "Exit" option
        values.append(APP_EXIT_TUPLE)

        # run the dialog and handle its return value
        val = radiolist_dialog(title=title, values=values, text=text).run()
        if val is None:
            return None
        elif val is False:
            exit()
        elif val == '.':
            return curr_path
        else:
            curr_path = val

# get the "<NAME>: <TITLE>" title string from an 'infoCourse.json' file's loaded data (or load the data if given a PLCourse)
def get_course_title(infocourse_data):
    if isinstance(infocourse_data, PLCourse):
        with open(infocourse_data.path / 'infoCourse.json') as f:
            infocourse_data = jload(f)
    return '%s: %s' % (infocourse_data['name'], infocourse_data['title'])

# class to represent a PrairieLearn course
# https://github.com/PrairieLearn/PrairieLearn/blob/master/apps/prairielearn/src/schemas/schemas/infoCourse.json
class PLCourse:
    # initialize this PLCourse object
    def __init__(self, path):
        if not (path / 'infoCourse.json').is_file():
            error("Invalid PrairieLearn course path: %s" % path)
        self.path = path

    # run app for the home view of this PLCourse object
    def app_home(self):
        while True:
            with open(self.path / 'infoCourse.json') as f:
                data = jload(f)
            order = [('uuid','UUID'), ('name','Name'), ('title','Title')]
            text = '- <ansiblue>Path:</ansiblue> %s\n' % self.path
            text += '\n'.join('- <ansiblue>%s:</ansiblue> %s' % (s, data[k]) for k, s in order)
            text += '\n- <ansiblue>Topics:</ansiblue> %s' % {True:'None', False:', '.join(data['topics'])}[len(data['topics']) == 0]
            pass # TODO ADD OTHER COURSE INFO
            values = [
                ('course_instances', HTML("<ansigreen>View Course Instances</ansigreen>")),
                ('questions', HTML('<ansigreen>View Questions</ansigreen>')),
                APP_EXIT_TUPLE,
            ]
            text = HTML(text)
            val = radiolist_dialog(title=get_course_title(data), text=text, values=values).run()
            if val is None:
                break
            elif val is False:
                exit()
            elif val == 'course_instances':
                self.app_course_instances()
            elif val == 'questions':
                self.app_questions()
            else:
                error("Invalid selection: %s" % val)

    # run app for course instances view
    def app_course_instances(self):
        while True:
            title = "Course Instances (%s)" % get_course_title(self)
            course_instances_data = dict()
            for child in self.path.glob('courseInstances/*'):
                with open(child / 'infoCourseInstance.json') as f:
                    course_instances_data[child] = jload(f)
            text = '- <ansiblue>Number of Course Instances:</ansiblue> %d' % len(course_instances_data)
            text = HTML(text)
            values = sorted(((PLCourseInstance(p,self), HTML('<ansigreen>%s</ansigreen> (%s)' % (course_instances_data[p]['longName'], p.name))) for p in course_instances_data), key=lambda x: x[1].value.lower())
            values.append(APP_EXIT_TUPLE)
            val = radiolist_dialog(title=title, text=text, values=values).run()
            if val is None:
                break
            elif val is False:
                exit()
            else:
                val.app_home()

    # run app for questions view
    def app_questions(self):
        while True:
            title = "Questions (%s)" % get_course_title(self)
            questions_data = dict()
            for p in (self.path / 'questions').rglob('question.html'):
                with open(p.parent / 'info.json') as f:
                    questions_data[p.parent] = jload(f)
            text = '- <ansiblue>Number of Questions:</ansiblue> %d' % len(questions_data)
            text = HTML(text)
            values = sorted(((PLQuestion(p,self), HTML('<ansigreen>%s</ansigreen> (%s)' % (questions_data[p]['title'], p.name))) for p in questions_data), key=lambda x: x[1].value.lower())
            values.append(APP_EXIT_TUPLE)
            val = radiolist_dialog(title=title, text=text, values=values).run()
            if val is None:
                break
            elif val is False:
                exit()
            else:
                val.app_home()

# get the "<NAME>" title string from an 'infoCourseInstance.json' file's loaded data (or load the data if given a PLCourseInstance)
def get_course_instance_title(infocourseinstance_data):
    if isinstance(infocourseinstance_data, PLCourseInstance):
        with open(infocourseinstance_data.path / 'infoCourseInstance.json') as f:
            infocourseinstance_data = jload(f)
    return infocourseinstance_data['longName']

# class to represent a PrairieLearn course instance
# https://github.com/PrairieLearn/PrairieLearn/blob/master/apps/prairielearn/src/schemas/schemas/infoCourseInstance.json
class PLCourseInstance:
    # initialize this PLCourseInstance object
    def __init__(self, path, course):
        if not (path / 'infoCourseInstance.json').is_file():
            error("Invalid PrairieLearn course instance path: %s" % path)
        self.path = path; self.course = course

    # run app for the home view of this PLCourseInstance object
    def app_home(self):
        while True:
            with open(self.path / 'infoCourseInstance.json') as f:
                data = jload(f)
            order = [('uuid','UUID'), ('longName','Long Name')]
            text = '- <ansiblue>Path:</ansiblue> %s\n' % self.path
            text += '\n'.join('- <ansiblue>%s:</ansiblue> %s' % (s, data[k]) for k, s in order)
            pass # TODO ADD OTHER COURSE INSTANCE INFO
            values = [
                ('assessments', HTML('<ansigreen>View Assessments</ansigreen>')),
                APP_EXIT_TUPLE,
            ]
            text = HTML(text)
            val = radiolist_dialog(title='Course Instance: %s' % get_course_instance_title(data), text=text, values=values).run()
            if val is None:
                break
            elif val is False:
                exit()
            elif val == 'assessments':
                self.app_assessments()
            else:
                error("Invalid selection: %s" % val)

    # run app for assessments view
    def app_assessments(self):
        while True:
            title = "Assessments (%s)" % get_course_instance_title(self)
            assessments_data = dict()
            for p in (self.path / 'assessments').rglob('infoAssessment.json'):
                with open(p) as f:
                    assessments_data[p.parent] = jload(f)
            text = '- <ansiblue>Number of Assessments:</ansiblue> %d' % len(assessments_data)
            text = HTML(text)
            values = sorted(((PLAssessment(p,self), HTML('<ansigreen>%s %s</ansigreen> - %s (%s)' % (assessments_data[p]['set'], assessments_data[p]['number'], assessments_data[p]['title'], assessments_data[p]['type']))) for p in assessments_data), key=lambda x: x[1].value.lower())
            values.append(APP_EXIT_TUPLE)
            val = radiolist_dialog(title=title, text=text, values=values).run()
            if val is None:
                break
            elif val is False:
                exit()
            else:
                val.app_home()

# get the "<SET> <NUMBER> (<TITLE>)" title string from an 'infoAssessment.json' file's loaded data (or load the data if given a PLAssessment)
def get_assessment_title(assessment_data):
    if isinstance(assessment_data, PLAssessment):
        with open(assessment_data.path / 'infoAssessment.json') as f:
            assessment_data = jload(f)
    return '%s %s (%s)' % (assessment_data['set'], assessment_data['number'], assessment_data['title'])

# class to represent a PrairieLearn assessment
# https://github.com/PrairieLearn/PrairieLearn/blob/master/apps/prairielearn/src/schemas/schemas/infoAssessment.json
class PLAssessment:
    # initialize this PLAssessment object
    def __init__(self, path, course_instance):
        if not (path / 'infoAssessment.json').is_file():
            error("Invalid PrairieLearn assessment path: %s" % path)
        self.path = path; self.course_instance = course_instance

    # run app for home view of this PLAssessment object
    def app_home(self):
        while True:
            with open(self.path / 'infoAssessment.json') as f:
                data = jload(f)
            order = [('uuid','UUID'), ('type','Type'), ('set','Set'), ('number','Number'), ('title','Title')]
            text = '- <ansiblue>Path:</ansiblue> %s\n' % self.path
            text += '\n'.join('- <ansiblue>%s:</ansiblue> %s' % (s, data[k]) for k, s in order)
            pass # TODO ADD OTHER ASSESSMENT INFO
            values = [
                ('zones', HTML('<ansigreen>View Zones</ansigreen>')),
                APP_EXIT_TUPLE,
            ]
            text = HTML(text)
            val = radiolist_dialog(title='Assessment: %s' % get_assessment_title(data), text=text, values=values).run()
            if val is None:
                break
            elif val is False:
                exit()
            elif val == 'zones':
                self.app_zones()
            else:
                error("Invalid selection: %s" % val)

    # run app for zones view
    def app_zones(self):
        while True:
            with open(self.path / 'infoAssessment.json') as f:
                data = jload(f)
            text = '- <ansiblue>Number of Zones:</ansiblue> %d' % len(data['zones'])
            text = HTML(text)
            values = [(PLZone(zone_data,self), HTML('<ansigreen>%s</ansigreen>' % zone_data['title'])) for zone_data in data['zones']]
            values.append(APP_EXIT_TUPLE)
            val = radiolist_dialog(title="Zones (%s)" % get_assessment_title(self), text=text, values=values).run()
            if val is None:
                break
            elif val is False:
                exit()
            else:
                val.app_home()

# class to represent a PrairieLearn assessment zone
class PLZone:
    # initialize this PLZone object
    def __init__(self, data, assessment):
        self.data = data; self.assessment = assessment

    # run app for home view of this PLZone object
    def app_home(self):
        while True:
            print("TODO"); exit() # TODO

# get the "<NAME>" title string from an 'info.json' file's loaded data (or load the data if given a PLQuestion)
def get_question_title(info_data):
    if isinstance(info_data, PLQuestion):
        with open(info_data.path / 'info.json') as f:
            info_data = jload(f)
    return info_data['title']

# class to represent a PrairieLearn question
# https://github.com/PrairieLearn/PrairieLearn/blob/master/apps/prairielearn/src/schemas/schemas/infoQuestion.json
class PLQuestion:
    # initialize this PLQuestion object
    def __init__(self, path, course):
        if not (path / 'question.html').is_file() or not (path / 'info.json').is_file():
            error("Invalid PrairieLearn question path: %s" % path)
        self.path = path; self.course = course

    # run app for home view of this PLQuestion object
    def app_home(self):
        while True:
            with open(self.path / 'info.json') as f:
                data = jload(f)
            order = [('uuid','UUID'), ('title','Title')]
            text = '- <ansiblue>Path:</ansiblue> %s\n' % self.path
            text += '\n'.join('- <ansiblue>%s:</ansiblue> %s' % (s, data[k]) for k, s in order)
            pass # TODO ADD OTHER COURSE INSTANCE INFO
            values = [
                APP_EXIT_TUPLE,
            ]
            text = HTML(text)
            val = radiolist_dialog(title='Question: %s' % get_question_title(data), text=text, values=values).run()
            if val is None:
                break
            elif val is False:
                exit()
            else:
                error("Invalid selection: %s" % val)

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
    pl_course.app_home()

# run main program
if __name__ == "__main__":
    main()
