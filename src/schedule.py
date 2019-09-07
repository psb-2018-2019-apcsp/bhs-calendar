#!/usr/bin/env python3
#
# schedule.py
#

"""Create 2019-2020 BHS schedule webpage."""

import collections
import csv
import datetime
import os
import re
import sys

__author__ = "David C. Petty & 2018-2019 BHS APCSP"
__copyright__ = "Copyright 2019, David C. Petty"
__license__ = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
__version__ = "0.1.0"
__maintainer__ = "David C. Petty"
__email__ = "david_petty@psbma.org"
__status__ = "Hack"


class Heading:
    """Encodes parsed schedule column heading into: weekday, week, cohort,
    e.g. parse 'Monday A BHS'. If heading is e.g. 'Monday A BHS STEAM',
    include lunch, otherwise Use default_lunch when only 3 tokens.
    (This allows for two different heading formats.)"""

    __regex3 = r'(\S+)\s+(\S+)\s+(\S+)'     # 3 space-separated tokens
    __regex4 = __regex3 + r'\s+(\S+)'       # 4 space-separated tokens

    def __init__(self, heading, default_lunch=None):
        """Initialize parsed schedule column heading."""
        match3 = re.match(self.__regex3, heading)
        assert match3, f"Heading '{heading}' must match regex '{self.__regex3}'"
        match4 = re.match(self.__regex4, heading)
        self._weekday = match3.group(1)     # weekday from heading
        self._week = match3.group(2)        # week from heading
        self._cohort = match3.group(3)      # cohort from heading
        self._lunch = match4.group(4) \
            if match4 else default_lunch    # lunch from heading, or default

    @property
    def weekday(self):
        """Return weekday string."""
        return self._weekday
        
    @property
    def week(self):
        """Return week string."""
        return self._week

    @property
    def cohort(self):
        """Return cohort string."""
        return self._cohort

    def _is_cohort(self, cohort):
        """Return true if self._cohort contains cohort."""
        return cohort.upper() in self.cohort.upper()

    def is_bhs(self): return self._is_cohort('BHS')
    def is_red(self): return self._is_cohort('RED')
    def is_blu(self): return self._is_cohort('BLU')

    @property
    def lunch(self):
        """Return lunch string."""
        return self._lunch

    @property
    def key(self):
        """Return cohort + lunch[0] string, or just cohort if not lunch."""
        return f"{self.cohort}-{self.lunch[0]}" if self.lunch else self.cohort

    def __str__(self):
        """Return string representation of Heading."""
        return f"{self.weekday}|{self.week}|{self.cohort}|{self.lunch}"

    __repr__ = __str__


class Block:
    """Encodes data on schedule blocks with useful @properties and strs."""

    def __init__(self, name, start, end, school, column, day, lunch):
        """Initialize schedule block class."""
        self._name = name               # block name
        self._start = start             # start minute
        self._end = end                 # end minute
        self._school = school           # which school cohort is at
        self._column = column           # column of _schedule
        self._day = day                 # day name
        self._lunch = lunch             # lunch name

    @property
    def name(self):
        """Return name string."""
        return self._name

    @property
    def start(self):
        """Return start minute."""
        return self._start

    @start.setter
    def start(self, value):
        """Set start minute."""
        self._start = value

    @property
    def end(self):
        """Return end minute."""
        return self._end

    @end.setter
    def end(self, value):
        """Set end minute."""
        self._end = value

    @property
    def school(self):
        """Return school on [None, 'BHS', 'OLS', 'PB2O', 'PO2B']."""
        return self._school

    @property
    def column(self):
        """Return column number."""
        return self._column

    @property
    def day(self):
        """Return day string."""
        return self._day

    @property
    def lunch(self):
        """Return lunch string."""
        return self._lunch

    def _is_name(self, names, length=None):
        """Return True if self._name (conditionally sliced) is in names."""
        nsl = self._name[:length] if length else self._name
        return nsl.upper() in [p.upper() for p in names]

    @property
    def is_passing(self):
        """Return True if self._name is any of passing block names."""
        return self._is_name(['P', '?', ], 1)

    @property
    def is_passing_split(self):
        """Return True if self._name is any of split passing block names."""
        return self._is_name(['PS', ])

    @property
    def is_passing_question(self):
        """Return True if self._name is any of question passing block names."""
        return self._is_name(['?', ])

    @property
    def is_school_passing(self):
        """Return True if self._name is any of school passing block names."""
        return self._is_name(['PB2O', 'PO2B', ])

    @property
    def is_lunch(self):
        """Return True if self._name is any of lunch block names."""
        return self._is_name(['L', ], 1)

    @property
    def duration(self):
        """Return duration of this block."""
        return self._end - self._start + 1

    @property
    def duration_str(self):
        """Return string for duration."""
        start = datetime.time(self._start // 60, self._start % 60) \
            .strftime('%I:%M')          # %p
        end = datetime.time((self._end + 1) // 60, (self._end + 1) % 60) \
            .strftime('%I:%M')          # %p
        return f"{start}-{end}"

    @property
    def html_str(self):
        """Return HTML cell string representation of block."""
        return f"{self._name}<br />" \
            f"{self.duration_str}<br />" \
            f"{self.duration}"

    def __str__(self):
        """Return string representation of Block."""
        return f"{self._name}-" \
            f"{self.duration_str}-" \
            f"{self.duration}-" \
            f"{self._school}-" \
            f"({Heading(self._day, self._lunch)})-" \
            f"{self._column}"

    __repr__ = __str__


class Schedule:
    """2019-2020 BHS Schedule."""

    def __init__(self, csvfile,
                 datadir='../data', wwwdir='../www', merged=False):
        """Initialize Schedule class for csvfile .CSV file, including
        reading csvfile .CSV file from datadir and writing csvfile .HTML
        file to wwwdir. The .CSV file follows the following format:

            STEAM,Monday A BHS,Monday A Red,Monday A Blue,Tuesday A BHS, ...
            7:30 AM,Z1,Z1,,Z2, ...
            ...

        OR

            BOTH,Monday A BHS STEAM,Monday A Red STEAM,Monday A Blue STEAM, ...
            7:30 AM,Z1,Z1,, ...
            ...

        where the 0th row is a header with schedule name, followed by triples
        of cohorts for as many cycle days as there are and the subsequent
        rows are times (in minutes) followed by triples of block names (or
        blank) for that cohort for that minute for that cycle day."""

        # Symbolic constants
        self._webpage_format = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="description" content="Brookline High School 2018-2019 APCSP bhs-schedule">
    <meta name="keyword" content="Brookline High School,2018-2019 APCSP,bhs-schedule">
    <title>2019-2020 BHS Schedule</title>
    <link href="https://fonts.googleapis.com/css?family=Source+Sans+Pro:400,600&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css?family=Lato:400,700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css?family=Saira+Extra+Condensed:200,400&display=swap" rel="stylesheet">
    <link href="./styles/schedule.css" rel="stylesheet">
    <script src="./scripts/schedule.js"></script>
  </head>
  <!-- http://patorjk.com/software/taag/    # ASCII art generator

 /$$$$$$$  /$$   /$$  /$$$$$$         /$$$$$$            /$$                       /$$           /$$          
| $$__  $$| $$  | $$ /$$__  $$       /$$__  $$          | $$                      | $$          | $$          
| $$  \ $$| $$  | $$| $$  \__/      | $$  \__/  /$$$$$$$| $$$$$$$   /$$$$$$   /$$$$$$$ /$$   /$$| $$  /$$$$$$ 
| $$$$$$$ | $$$$$$$$|  $$$$$$       |  $$$$$$  /$$_____/| $$__  $$ /$$__  $$ /$$__  $$| $$  | $$| $$ /$$__  $$
| $$__  $$| $$__  $$ \____  $$       \____  $$| $$      | $$  \ $$| $$$$$$$$| $$  | $$| $$  | $$| $$| $$$$$$$$
| $$  \ $$| $$  | $$ /$$  \ $$       /$$  \ $$| $$      | $$  | $$| $$_____/| $$  | $$| $$  | $$| $$| $$_____/
| $$$$$$$/| $$  | $$|  $$$$$$/      |  $$$$$$/|  $$$$$$$| $$  | $$|  $$$$$$$|  $$$$$$$|  $$$$$$/| $$|  $$$$$$$
|_______/ |__/  |__/ \______/        \______/  \_______/|__/  |__/ \_______/ \_______/ \______/ |__/ \_______/
        /$$$$$$   /$$$$$$   /$$$$$$    /$$    /$$$$$$          /$$$$$$   /$$$$$$   /$$$$$$   /$$$$$$          
       /$$__  $$ /$$$_  $$ /$$$_  $$ /$$$$   /$$__  $$        /$$__  $$ /$$$_  $$ /$$__  $$ /$$$_  $$         
      |__/  \ $$| $$$$\ $$| $$$$\ $$|_  $$  | $$  \ $$       |__/  \ $$| $$$$\ $$|__/  \ $$| $$$$\ $$         
        /$$$$$$/| $$ $$ $$| $$ $$ $$  | $$  |  $$$$$$$ /$$$$$$ /$$$$$$/| $$ $$ $$  /$$$$$$/| $$ $$ $$         
       /$$____/ | $$\ $$$$| $$\ $$$$  | $$   \____  $$|______//$$____/ | $$\ $$$$ /$$____/ | $$\ $$$$         
      | $$      | $$ \ $$$| $$ \ $$$  | $$   /$$  \ $$       | $$      | $$ \ $$$| $$      | $$ \ $$$         
      | $$$$$$$$|  $$$$$$/|  $$$$$$/ /$$$$$$|  $$$$$$/       | $$$$$$$$|  $$$$$$/| $$$$$$$$|  $$$$$$/         
      |________/ \______/  \______/ |______/ \______/        |________/ \______/ |________/ \______/          

{comment}
  -->
  <body>
    <!-- HEADER -->
    <header>
      <section>
        <h1>Brookline High School &mdash; 2019-2020 Schedule</h1>
      </section>
    </header>
    <!-- NAV --><!--
    <nav>
      <section>
        <h2>Nav</h2>
        <article>
          <p>Content...</p>
        </article>
      </section>
    </nav> -->
    <!-- ASIDE --><!--
    <aside>
      <section>
        <h2>Aside</h2>
        <article>
          <p>Content...</p>
        </article>
      </section>
    </aside> -->
    <!-- MAIN -->
    <main>
      <h2>{heading}</h2>
{main}
    </main>
    <!-- FOOTER -->
    <footer>
      <section>
        <h2>{filename} &mdash; {date_time}</h2>
        <article>
          <p>This file is available on <a href="https://github.com/psb-2018-2019-apcsp/bhs-calendar/">Github</a> based on this <a href="{csvpath}">CSV</a>&hellip;</p>
{extra}
          <ul>
            <li><span class="swatch short">&nbsp;</span> &mdash; passing time &lt; 5 minutes</li>
            <li><span class="swatch split">&nbsp;</span> &mdash; split lunch passing time (matched to other passing time for that day in that building)</li>
            <li><span class="swatch question">&nbsp;</span> &mdash; zero-length passing time adjusted by removal from lunch block or preceeding block (matched to other passing time for that day in that building)</li>
          </ul>
        </article>
      </section>
    </footer>
  </body>
</html>
"""
        self._days_format = """
<section class="days">
{days}
</section>
"""
        self._cohorts_format = """
<article class="day">
  <h3>{column}</h3>
  <div class="cohorts">
{cohorts}
  </div>
</article>
"""
        self._blocks_format = """
<div class="cohort">
  <div class="{bs}">
    <h4>{cohort}</h4>
{blocks}
  </div>
</div>
"""
        self._block_format = """
<p class="{cls}" style="height: {pad}px;" title="{title}">{text}</p>
"""
        self._total_format = """
<p class="{cls}" title="{title}">{text}</p>
"""
        self._init(csvfile, datadir, wwwdir, merged)

    def _init(self, csvfile, datadir, wwwdir, merged):
        """Initialize webpage parameters."""

        filename, extension = os.path.splitext(csvfile)
        self._filename, self._datadir, self._wwwdir = filename, datadir, wwwdir
        assert extension == '.csv', f"Bad extension: '{extension}' != '.csv'"

        self._csvpath = os.path.join(self._datadir, self._filename + '.csv')
        self._wwwpath = os.path.join(self._wwwdir, self._filename
                                     + ('-merge.html' if merged else '.html'))

        self._schedule = self._csv(self._csvpath)       # parse .CSV file
        assert len(set(len(l) for l in self._schedule)) == 1, \
            f"self._schedule not rectangular (line lengths are " \
            f"{set(len(l) for l in self._schedule)})"

        # Format comment & extra.
        self._formatted_date_time = datetime.datetime.now().strftime('%c')
        # strftime('%a-%Y/%m/%d-%I:%M:%S%p%z')
        csv_comment = ''
        for row in self._schedule:
            csv_comment += f"{row}\n"
        self._comment = f"Created by {type(self).__name__} " \
            f"on {self._formatted_date_time} " \
            f"from CSV{':'} \n{csv_comment}"
        self._extra = ''

        # Create blocks _dict w/ for each column of _schedule keyed w/ heading
        # w/ block entries for name, start, end, school, col, day, lunch
        self._dict = collections.OrderedDict()          # maintain heading order
        pb2o, po2b = 'PB2O'.upper(), 'PO2B'.upper()     # to check for school
        for col in range(1, max([len(row) for row in self._schedule])):
            blocks = list()
            day, name = self._schedule[0][col], self._schedule[1][col]
            lunch = Heading(day, self._schedule[0][0]).lunch

            # First find pb2o and po2b inter-school passing.
            first_b2o, last_b2o, first_o2b, last_o2b = None, None, None, None
            for row in self._schedule[1:]:              # not including header
                # Look for inter-school passing.
                if pb2o in row[col]:
                    if not first_b2o:
                        first_b2o = last_b2o = self._minute(row[0])
                    else:
                        last_b2o = self._minute(row[0])
                if po2b in row[col]:
                    if not first_o2b:
                        first_o2b = last_o2b = self._minute(row[0])
                    else:
                        last_o2b = self._minute(row[0])

            # Next find block start and end.
            start = end = self._minute(self._schedule[1][0])
            for row in self._schedule[1:]:              # not including header
                # Look for end of block.
                if row[col] == name:
                    end = self._minute(row[0])
                else:
                    if name:
                        # Cohort school in column of _schedule is:
                        # OLS, if RED column and above PB2O (or no PB2O); or
                        # OLS, if BLUE column and below PO2B (or no PO2B); or
                        # PB2O or PO2B, if passing schools;
                        # otherwise, BHS.
                        # RED_FLAG: use Heading cohort tests
                        school = name if pb2o in name or po2b in name else \
                            'OLS' if ('RED' in day.upper() and
                                      (last_b2o is None or start > last_b2o)) \
                            or ('BLUE' in day.upper() and
                                (first_o2b is None or end < first_o2b)) \
                            else 'BHS'
                        block = Block(name, start, end, school, col, day, lunch)
                        blocks.append(block)
                    name = row[col]
                    start = end = self._minute(row[0])
            self._dict[day] = blocks
        print(self._dict)                               # TODO: debugging
        # Merge passing time with lunch
        if merged:
            self._merge()

        # Format webpage based on _schedule and _dict and write it out.
        self._page = self._webpage(True)
        self.write(self._wwwpath)

    # ///////////////////////////// UTILITIES //////////////////////////////

    # https://realpython.com/instance-class-and-static-methods-demystified/

    @staticmethod
    def _minute(time):
        """Return minute number for time string, e.g. '7:30 AM' yields 450."""
        parsed = datetime.datetime.strptime(time, '%I:%M %p')
        return parsed.hour * 60 + parsed.minute

    @staticmethod
    def _wrap(text, indent=0, wrap=80, delimiter=' '):
        """Return text, broken into lines of no more than wrap characters,
        indented by indent spaces. Indent only, if wrap <= 0."""
        length, start, last, space, result = wrap - indent, 0, 0, delimiter, ''
        for i, c in enumerate(text.strip()):
            if 0 < length <= i - start:
                result += '\n' + space * indent + text[start: last]
                start = last
            if c == delimiter:
                last = i + 1
            if c == '\n':
                result += '\n' + space * indent + text[start: i]
                start = last = i + 1
        result += '\n' + space * indent + text.strip()[start:]
        return result[1:]

    @staticmethod
    def _scale(x, factor=3):
        """Return x scaled by factor and rounded to nearest int."""
        return round(x * factor)

    @staticmethod
    def _csv(csvpath):
        """Return csv file as 2d list."""
        with open(csvpath) as csvfile:
            schedule, schedulereader = list(), csv.reader(csvfile)
            for row in schedulereader:
                schedule.append(row)
        return schedule

    @staticmethod
    def _totals(block_dict, cohorts, default_lunch=None):
        """Return dict of expressions for total for each block letter,
        including lunch ('L'), as entries in a dict keyed by cohorts."""
        totals = dict()
        for name in cohorts:                            # cohort name
            totals[name] = dict()
            for key, blocks in block_dict.items():
                for block in blocks:
                    key = Heading(block.day, default_lunch).key
                    # Match block letter(s) followed by number(s).
                    match = re.match(r'(\D+)\d+$', block.name)
                    if key == name and match:
                        c = match.group(1)
                        subtotal = totals[name].get(c, '')
                        totals[name][c] = subtotal \
                            + ('+' if subtotal else '') \
                            + str(block.duration)
                    # Handle lunches separately.
                    if key == name and block.is_lunch:
                        subtotal = totals[name].get('L', '')
                        totals[name]['L'] = subtotal \
                            + ('+' if subtotal else '') \
                            + str(block.duration)
        return totals

    def _merge(self):
        """Merge passing time with lunch in self._dict."""
        for key in self._dict.keys():
            but1_index, and1_index = None, None
            for i, block in enumerate(self._dict[key]):
                if block.is_lunch:
                    if i > 0:
                        but1, but1_index = self._dict[key][i - 1], i - 1
                        if but1.is_passing and not but1.is_school_passing:
                            self._dict[key][i].start = but1.start
                    if i < len(self._dict[key]):
                        and1, and1_index = self._dict[key][i + 1], i + 1
                        if and1.is_passing and not and1.is_school_passing:
                            self._dict[key][i].end = and1.end
            if and1_index is not None and not and1.is_school_passing:
                del(self._dict[key][and1_index])
            if but1_index is not None and not but1.is_school_passing:
                del(self._dict[key][but1_index])

    def _webpage(self, verbose=False):
        """Return webpage based on _schedule and _dict.
        Note: there are three cohorts, hence the 'i % 3' code."""

        # Format days and cohorts.
        days = ''
        # Process every column, keeping three cohorts together for every day.
        for i, key in enumerate(self._schedule[0][1:]):
            if i % 3 == 0:                              # start of a new day
                cohorts = ''
            head = Heading(key, self._schedule[0][0])
            column = f"{head.weekday} - {head.week} - {head.lunch[0]}"
            style = f"blocks"
            cohort = head.cohort
            # Add skip to empty paragraph for empty block at start of day.
            skip = self._scale(self._dict[key][0].start
                - self._minute(self._schedule[1][0]))
            skip += 2 if skip else 0                    # adjust for border(s)
            blocks = \
                f"""    <p class="start" style="height: {skip}px;"></p>\n"""
            # Add a paragraph for every block to cohort.
            for block in self._dict[key]:
                name = block.name.upper()
                # Display passing blocks w/ no content, just mouse-over title.
                if block.is_passing and not block.is_school_passing:
                    cls = f"passing"
                    text = ''
                    if block.is_passing_split:
                        cls += f" split"
                    if block.is_passing_question:
                        cls += f" question"
                    if block.duration < 5:
                        cls += f" short"
                else:
                    school = block.school
                    cls = f"school-{name.lower()}" \
                        if block.is_school_passing \
                        else f"block cohort-{cohort.lower()} " \
                            f"school-{school.lower()}"
                    text = f"{block.name}<br />" \
                        f"{block.duration_str}<br />" \
                        f"{block.duration}"
                    if block.is_lunch:                  # add lunch class
                        cls += f" lunch"
                pad = self._scale(block.duration)
                title = f"{name} @ " \
                    f"{school}: " \
                    f"{block.duration_str} = " \
                    f"{block.duration}"
                blocks += self._wrap(self._block_format.strip().format(
                    cls=cls, pad=pad, title=title, text=text),
                        4, 0) + '\n'
            cohorts += self._wrap(self._blocks_format.strip().format(
                bs=style, cohort=cohort, blocks=blocks.rstrip()), 4, 0) + '\n'
            if i % 3 == 2:                              # end of cohort
                days += self._wrap(self._cohorts_format.strip().format(
                    column=column, cohorts=cohorts.rstrip()), 2, 0) + '\n'

        # Names are Heading.key from _dict.keys().
        names = collections.OrderedDict()               # maintain key order
        for key in self._dict.keys():
            names[f"{Heading(key, self._schedule[0][0]).key}"] = None

        # Calculate block totals by cohort and add cohort columns for totals.
        totals = self._totals(self._dict, names.keys(), self._schedule[0][0])
        column = 'Totals'
        cohorts = ''
        style = f"totals"
        keys = set([k for n in names for k in totals[n].keys()])
        for cohort in names:
            blocks = ''
            for key in sorted(keys):
                value = eval(totals[cohort].get(key, '0'))
                cls = 'total'
                title = text = f"{key} = {value:03d}"
                blocks += self._wrap(self._total_format.strip().format(
                    cls=cls, title=title, text=text),
                            4, 0) + '\n'        
            cohorts += self._wrap(self._blocks_format.strip().format(
                bs=style, cohort=cohort, blocks=blocks.rstrip()), 4, 0) + '\n'

        # Format days.
        days += self._wrap(self._cohorts_format.strip().format(
            column=column, cohorts=cohorts.rstrip()), 2, 0) + '\n'

        # Conditionally format extra with calculation of totals.
        for c, t in totals.items():
            self._extra += ('\n' if self._extra else '') + f"{c}:"
            line = ''
            for k in sorted(t.keys()):
                line += f"\n  {k:3s} = {eval(t[k]):3d} = {t[k]}"
            self._extra += line
        print(self._extra)
        if verbose:
            self._extra = f"<pre class=\"calculations\">{self._extra}</pre>"

        # Conditionally format extra with table of non-passing blocks.
        table_format = """<hr class="no-pass" />\n""" \
            """<table class="no-pass">\n{header}{rows}</table>"""
        row_format = """  <tr>\n{row}  </tr>\n"""
        cell_format = """    <t{hd} title="{title}">{cell}</t{hd}>\n"""

        # Format header.
        row = ''
        for key in self._dict:
            row += cell_format.format(cell=f"{key}", title=f"{key}", hd='h')
        header = row_format.format(row=row)

        # Copy self._dict to schedule, removing all passing-time blocks.
        schedule = collections.OrderedDict()
        for key in self._dict:
            schedule[key] = [b for b in self._dict[key] if not b.is_passing]
        length = max((len(schedule[key]) for key in schedule))

        # Format rows.
        rows = ''
        for i in range(length):
            row = ''
            for key in schedule:
                column = schedule[key]
                cell = column[i].html_str if i < len(column) else ''
                title = column[i] if i < len(column) else ''
                row += cell_format.format(cell=cell, title=title, hd='d')
            rows += row_format.format(row=row)

        # Format table.
        table = self._wrap(table_format.format(header=header, rows=rows), 10, 0)

        if verbose:
            self._extra += f"\n{table}"

        # Format <main>.
        main = self._wrap(self._days_format.strip().format(
            days=days.rstrip()), 6, 0)

        # Return formatted webpage.
        heading = f"{self._schedule[0][0]} Lunch"
        comment = self._wrap(self._comment, 4, 0)
        filename = self._filename
        date_time = self._formatted_date_time
        csvpath = self._csvpath
        extra = self._extra
        return self._webpage_format.strip().format(
            comment=comment, heading=heading, main=main,
            filename=filename, date_time=date_time, csvpath=csvpath,
            extra=extra)

    def write(self, outpath=None):
        """Write self.page to outpath, or print if outpath is None."""
        # Write or print self.code.
        if outpath:
            with open(outpath, 'w') as outfile:
                outfile.write(self._page)
            print(outpath)
        else:
            print(self.page)


if __name__ == '__main__':
    is_idle, is_pycharm, is_jupyter = (
        'idlelib' in sys.modules,
        int(os.getenv('PYCHARM', 0)),
        '__file__' not in globals()
        )
    if is_idle or is_pycharm or is_jupyter:
        # human_schedule = Schedule('schedule-1b-bhs-2019-2020-human-split.csv')
        # steam_schedule = Schedule('schedule-1b-bhs-2019-2020-steam-split.csv')
        # human_schedule = Schedule('schedule-1b-bhs-2019-2020-human-short.csv')
        # steam_schedule = Schedule('schedule-1b-bhs-2019-2020-steam-short.csv')
        # human_schedule = \
        #     Schedule('schedule-1b-bhs-2019-2020-human-merge.csv', merged=True)
        # steam_schedule = \
        #     Schedule('schedule-1b-bhs-2019-2020-steam-merge.csv', merged=True)
        both_schedule = Schedule('schedule-1b-bhs-2019-2020-both.csv')
        both_schedule = \
            Schedule('schedule-1b-bhs-2019-2020-both.csv', merged=True)

        lipsum = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Quisque viverra ex vitae nisi volutpat, vitae elementum felis eleifend. Nullam laoreet ac nisl a dignissim. In sem libero, gravida commodo diam eu, egestas vehicula purus. Pellentesque laoreet maximus nunc, eget sollicitudin urna feugiat id. Sed aliquam purus ut leo pellentesque, euismod eleifend quam eleifend. Pellentesque eget urna sed nisl finibus facilisis. Aliquam consequat diam magna, in mollis leo posuere imperdiet. Ut fermentum bibendum pellentesque. Aenean eleifend massa nisi, et dictum justo sagittis id. Etiam sollicitudin et turpis at cursus. Proin nec est lectus. Nullam dui purus, imperdiet a mattis in, convallis dictum massa. Suspendisse nec fringilla nibh.

Quisque a purus et purus mattis venenatis non at tellus. Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Nullam tincidunt tincidunt bibendum. Fusce interdum lacus eu ex tincidunt auctor. Vestibulum efficitur libero sem, eu viverra est finibus vitae. Vivamus viverra imperdiet euismod. Fusce neque eros, vehicula ut leo aliquam, efficitur vestibulum velit.

Duis accumsan hendrerit leo non placerat. Donec pretium eros urna, in semper neque venenatis a. In hac habitasse platea dictumst. Mauris pharetra tellus purus, et ultrices neque feugiat quis. Donec sagittis rutrum ipsum, nec condimentum augue malesuada vitae. Fusce ornare cursus quam, et sollicitudin purus varius ac. Proin velit nunc, dictum sit amet purus nec, facilisis eleifend turpis. Cras at dui gravida dolor elementum congue in luctus magna. Pellentesque in eros et nibh lacinia luctus. Etiam finibus lacus ut imperdiet facilisis. Nulla facilisi. Etiam ac augue at dolor placerat aliquet. Morbi sit amet pellentesque libero. Etiam ante magna, mollis nec viverra vitae, consectetur ac dui.

""".replace(' ', ' ')
#         print('1234567890' * 8)
#         print('"{}"'.format(human_schedule._wrap(lipsum, 6)))
#         print(Block('FOO', 100, 199, 'BHS', 47, 'BAR BLAP FRAB', 'STEAM'))

# http://code.activestate.com/recipes/577070-bound-inner-classes/
# for a bound inner class decorator...
