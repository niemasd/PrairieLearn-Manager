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

# align two strings using Needleman-Wunsch
def align(s, t, match_score=1, mismatch_penalty=float('-inf'), gap_penalty=-1):
    # set things up, e.g. convert s and t to strings if not already
    diag = {True:match_score, False:mismatch_penalty} # diag[s[i] == t[j]] gets you the match score / mismatch penalty
    if not isinstance(s, str):
        s = str(s)
    if not isinstance(t, str):
        t = str(t)

    # perform DP, where cells are (score, i, j) tuples (or None if not yet calculated)
    dp = [[None for j in range(len(t)+1)] for i in range(len(s)+1)]
    dp[0][0] = (0, None, None)
    for i in range(len(s)):
        dp[i+1][0] = (gap_penalty * (i+1), i, 0)
    for j in range(len(t)):
        dp[0][j+1] = (gap_penalty * (j+1), 0, j)
    for i in range(len(s)):
        for j in range(len(t)):
            dp[i+1][j+1] = max((
                (dp[i][j][0] + diag[s[i] == t[j]], i, j), # match/mismatch
                (dp[i+1][j][0] + gap_penalty, i+1, j),    # gap in s
                (dp[i][j+1][0] + gap_penalty, i, j+1),    # gap in t
            ))

    # backtrack and return result (s_aln and t_aln need to be reversed before returning)
    s_aln = list(); t_aln = list(); i = len(s); j = len(t)
    while True:
        if i == 0 and j == 0:
            break
        if dp[i][j][1] == i:
            s_aln.append('-')
        else:
            s_aln.append(s[i-1])
        if dp[i][j][2] == j:
            t_aln.append('-')
        else:
            t_aln.append(t[j-1])
        DUMMY, i, j = dp[i][j]
    return ''.join(s_aln)[::-1], ''.join(t_aln)[::-1]

# find the root course folder given a subfolder
def find_course_path(orig_path):
    curr_path = orig_path
    while curr_path != ROOT_PATH:
        if (curr_path / 'infoCourse.json').is_file():
            return curr_path
        curr_path = curr_path.parent
    error("Unable to find root course folder: %s" % orig_path)

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
def get_course_title(x):
    if isinstance(x, PLCourse):
        x = x.get_info_data()
    return '%s: %s' % (x['name'], x['title'])

# class to represent a PrairieLearn course
# https://github.com/PrairieLearn/PrairieLearn/blob/master/apps/prairielearn/src/schemas/schemas/infoCourse.json
class PLCourse:
    # initialize this PLCourse object
    def __init__(self, path):
        if not (path / 'infoCourse.json').is_file():
            error("Invalid PrairieLearn course path: %s" % path)
        self.path = path

    # load and return the data from this course's 'infoCourse.json' file
    def get_info_data(self):
        with open(self.path / 'infoCourse.json') as f:
            return jload(f)

    # iterate over course instances in this course
    def iter_course_instances(self):
        for p in self.path.glob('courseInstances/*/infoCourseInstance.json'):
            yield PLCourseInstance(p.parent)

    # iterate over questions in this course
    def iter_questions(self):
        for p in (self.path / 'questions').rglob('question.html'):
            yield PLQuestion(p.parent)

    # run app for the home view of this PLCourse object
    def app_home(self):
        while True:
            data = self.get_info_data()
            order = [('uuid','UUID'), ('comment','Comment'), ('name','Name'), ('title','Title')]
            text = '- <ansiblue>Path:</ansiblue> %s' % self.path
            for k, s in order:
                if k in data:
                    text += '\n- <ansiblue>%s:</ansiblue> %s' % (s, data[k])
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
            title = "Course Instances - %s" % get_course_title(self)
            course_instances_data = {ci:ci.get_info_data() for ci in self.iter_course_instances()}
            text = '- <ansiblue>Number of Course Instances:</ansiblue> %d' % len(course_instances_data)
            text = HTML(text)
            values = sorted(((ci, HTML('<ansigreen>%s</ansigreen> (%s)' % (d['longName'], ci.path.name))) for ci, d in course_instances_data.items()), key=lambda x: x[1].value.lower())
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
            title = "Questions - %s" % get_course_title(self)
            questions_data = {q:q.get_info_data() for q in self.iter_questions()}
            text = '- <ansiblue>Number of Questions:</ansiblue> %d' % len(questions_data)
            text = HTML(text)
            values = sorted(((q, HTML('<ansigreen>%s</ansigreen> (%s)' % (d['title'], q.path.name))) for q, d in questions_data.items()), key=lambda x: x[1].value.lower())
            values.append(APP_EXIT_TUPLE)
            val = radiolist_dialog(title=title, text=text, values=values).run()
            if val is None:
                break
            elif val is False:
                exit()
            else:
                val.app_home()

# get the "<NAME>" title string from an 'infoCourseInstance.json' file's loaded data (or load the data if given a PLCourseInstance)
def get_course_instance_title(x):
    if isinstance(x, PLCourseInstance):
        x = x.get_info_data()
    return x['longName']

# class to represent a PrairieLearn course instance
# https://github.com/PrairieLearn/PrairieLearn/blob/master/apps/prairielearn/src/schemas/schemas/infoCourseInstance.json
class PLCourseInstance:
    # initialize this PLCourseInstance object
    def __init__(self, path):
        if not (path / 'infoCourseInstance.json').is_file():
            error("Invalid PrairieLearn course instance path: %s" % path)
        self.path = path

    # iterate over access controls in this course instance
    def iter_access_controls(self):
        data = self.get_info_data()
        for access_data in data['allowAccess']:
            yield PLAccess(access_data, self.path / 'infoCourseInstance.json')

    # iterater over assessments in this course instance
    def iter_assessments(self):
        for p in (self.path / 'assessments').rglob('infoAssessment.json'):
            yield PLAssessment(p.parent)

    # load and return the data from this course instance's 'infoCourseInstance.json' file
    def get_info_data(self):
        with open(self.path / 'infoCourseInstance.json') as f:
            return jload(f)

    # run app for the home view of this PLCourseInstance object
    def app_home(self):
        while True:
            data = self.get_info_data()
            order = [('uuid','UUID'), ('comment','Comment'), ('longName','Long Name'), ('hideInEnrollPage','Hide in Enroll Page'), ('timezone','Time Zone')]
            text = '- <ansiblue>Path:</ansiblue> %s' % self.path
            for k, s in order:
                if k in data:
                    text += '\n- <ansiblue>%s:</ansiblue> %s' % (s, data[k])
            # TODO MOVE TO SEPARATE "View Access Controls" SELECTION SIMILAR TO HOW ZONES WORK IN ASSESSMENTS
            # TODO TO DO THE ABOVE, I SHOULD MAKE A PLAccess CLASS OR SOMETHING
            if 'allowAccess' in data:
                text += '\n- <ansiblue>Number of Access Controls:</ansiblue> %d' % len(data['allowAccess'])
            values = [
                ('access_controls', HTML('<ansigreen>View Access Controls</ansigreen>')),
                ('assessments', HTML('<ansigreen>View Assessments</ansigreen>')),
                APP_EXIT_TUPLE,
            ]
            text = HTML(text)
            val = radiolist_dialog(title='Course Instance - %s' % get_course_instance_title(data), text=text, values=values).run()
            if val is None:
                break
            elif val is False:
                exit()
            elif val == 'access_controls':
                self.app_access_controls()
            elif val == 'assessments':
                self.app_assessments()
            else:
                error("Invalid selection: %s" % val)

    # run app for access controls view
    def app_access_controls(self):
        while True:
            title = "Access Controls - %s" % get_course_instance_title(self)
            exit(1) # TODO

    # run app for assessments view
    def app_assessments(self):
        while True:
            title = "Assessments - %s" % get_course_instance_title(self)
            assessments_data = {a:a.get_info_data() for a in self.iter_assessments()}
            text = '- <ansiblue>Number of Assessments:</ansiblue> %d' % len(assessments_data)
            text = HTML(text)
            values = sorted(((a, HTML('<ansigreen>%s %s</ansigreen> - %s (%s)' % (d['set'], d['number'], d['title'], d['type']))) for a, d in assessments_data.items()), key=lambda x: x[1].value.lower())
            values.append(APP_EXIT_TUPLE)
            val = radiolist_dialog(title=title, text=text, values=values).run()
            if val is None:
                break
            elif val is False:
                exit()
            else:
                val.app_home()

# get the "<SET> <NUMBER> (<TITLE>)" title string from an 'infoAssessment.json' file's loaded data (or load the data if given a PLAssessment)
def get_assessment_title(x):
    if isinstance(x, PLAssessment):
        x = x.get_info_data()
    return '%s %s: %s' % (x['set'], x['number'], x['title'])

# class to represent a PrairieLearn assessment
# https://github.com/PrairieLearn/PrairieLearn/blob/master/apps/prairielearn/src/schemas/schemas/infoAssessment.json
class PLAssessment:
    # initialize this PLAssessment object
    def __init__(self, path):
        if not (path / 'infoAssessment.json').is_file():
            error("Invalid PrairieLearn assessment path: %s" % path)
        self.path = path

    # load and return the data from this assessment's 'infoAssessment.json' file
    def get_info_data(self):
        with open(self.path / 'infoAssessment.json') as f:
            return jload(f)

    # iterate over zones in this assessment
    def iter_zones(self):
        for zone_data in self.get_info_data()['zones']:
            yield PLZone(zone_data, self.path / 'infoAssessment.json')

    # run app for home view of this PLAssessment object
    def app_home(self):
        while True:
            data = self.get_info_data()
            order = [('uuid','UUID'), ('comment','Comment'), ('type','Type'), ('set','Set'), ('number','Number'), ('title','Title'), ('shuffleQuestions','Shuffle Questions'), ('allowRealTimeGrading','Allow Real-Time Grading')]
            text = '- <ansiblue>Path:</ansiblue> %s' % self.path
            for k, s in order:
                if k in data:
                    text += '\n- <ansiblue>%s:</ansiblue> %s' % (s, data[k])
            pass # TODO ADD OTHER ASSESSMENT INFO
            values = [
                ('zones', HTML('<ansigreen>View Zones</ansigreen>')),
                APP_EXIT_TUPLE,
            ]
            text = HTML(text)
            val = radiolist_dialog(title='Assessment - %s' % get_assessment_title(data), text=text, values=values).run()
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
            data = self.get_info_data()
            text = '- <ansiblue>Number of Zones:</ansiblue> %d' % len(data['zones'])
            text = HTML(text)
            values = [(z, HTML('<ansigreen>%s</ansigreen>' % z.get_data()['title'])) for z in self.iter_zones()]
            values.append(APP_EXIT_TUPLE)
            val = radiolist_dialog(title="Zones - %s" % get_assessment_title(self), text=text, values=values).run()
            if val is None:
                break
            elif val is False:
                exit()
            else:
                val.app_home()

# class to represent a PrairieLearn access control
class PLAccess:
    # initialize this PLAccess object
    def __init__(self, data, path):
        self.data = data; self.path = path

    # get the data defining this access control
    def get_data(self):
        return self.data

    # # run app for home view of this PLAccess object
    def app_home(self):
        while True:
            text = '- <ansiblue>Path:</ansiblue> %s' % self.path
            pass # TODO ADD OTHER ACCESS INFO
            text = HTML(text)
            valies = [
                APP_EXIT_TUPLE,
            ]
            val = radiolist_dialog(title=title, text=text, values=values).run()
            if val is None:
                break
            elif val is False:
                exit()
            else:
                error("Invalid selection: %s" % val)

# class to represent a PrairieLearn assessment zone
class PLZone:
    # initialize this PLZone object
    def __init__(self, data, path):
        self.data = data; self.path = path

    # get the data defining this zone
    def get_data(self):
        return self.data

    # iterate over questions in this zone
    def iter_questions(self):
        questions_path = find_course_path(self.path) / 'questions'
        if not questions_path.is_dir():
            error("Questions path not found: %s" % questions_path)
        for q_data in self.data['questions']:
            yield PLQuestion(questions_path / q_data['id'])

    # run app for home view of this PLZone object
    def app_home(self):
        while True:
            title = 'Zone - %s' % self.data['title']
            text = '- <ansiblue>Path:</ansiblue> %s' % self.path
            pass # TODO ADD OTHER ZONE INFO
            text = HTML(text)
            values = [
                ('questions', HTML('<ansigreen>View Questions</ansigreen>')),
                APP_EXIT_TUPLE,
            ]
            val = radiolist_dialog(title=title, text=text, values=values).run()
            if val is None:
                break
            elif val is False:
                exit()
            elif val == 'questions':
                self.app_questions()
            else:
                error("Invalid selection: %s" % val)

    # run app for questions view
    def app_questions(self):
        while True:
            title = "Questions - %s" % self.data['title']
            questions_data = {q:q.get_info_data() for q in self.iter_questions()}
            text = '- <ansiblue>Number of Questions:</ansiblue> %d' % len(questions_data)
            text = HTML(text)
            values = sorted(((q, HTML('<ansigreen>%s</ansigreen> (%s)' % (d['title'], q.path.name))) for q, d in questions_data.items()), key=lambda x: x[1].value.lower())
            values.append(APP_EXIT_TUPLE)
            val = radiolist_dialog(title=title, text=text, values=values).run()
            if val is None:
                break
            elif val is False:
                exit()
            else:
                val.app_home()

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
    def __init__(self, path):
        if not (path / 'question.html').is_file() or not (path / 'info.json').is_file():
            error("Invalid PrairieLearn question path: %s" % path)
        self.path = path

    # load and return the data from this question's 'info.json' file
    def get_info_data(self):
        with open(self.path / 'info.json') as f:
            return jload(f)

    # run app for home view of this PLQuestion object
    def app_home(self):
        while True:
            with open(self.path / 'info.json') as f:
                data = jload(f)
            order = [('uuid','UUID'), ('comment','Comment'), ('title','Title')]
            text = '- <ansiblue>Path:</ansiblue> %s' % self.path
            for k, s in order:
                if k in data:
                    text += '\n- <ansiblue>%s:</ansiblue> %s' % (s, data[k])
            pass # TODO ADD OTHER COURSE INSTANCE INFO
            values = [
                APP_EXIT_TUPLE,
            ]
            text = HTML(text)
            val = radiolist_dialog(title='Question - %s' % get_question_title(data), text=text, values=values).run()
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
