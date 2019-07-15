#!/usr/bin/env python3
#
# schedule.py
#

"""Create 2019-2020 BHS schedule webpage."""

import csv, datetime, os, re, sys

__author__ = "David C. Petty & 2019-2020 BHS APCSP"
__copyright__ = "Copyright 2019, David C. Petty"
__license__ = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
__version__ = "0.0.1"
__maintainer__ = "David C. Petty"
__email__ = "david_petty@psbma.org"
__status__ = "Hack"

# http://code.activestate.com/recipes/577070-bound-inner-classes/
# for a bound inner class decorator...

class Heading:
    """Encodes parsed schedule column heading into:
    weekday, week, cohort, and lunch."""

    __regex = r'(\S+)\s+(\S+)\s+(\S+)'

    def __init__(self, heading):
        """Initialize parsed schedule column heading."""
        match = re.match(self.__regex, heading)
        assert match, f"Heading '{heading}' must match regex '{self.__regex}'"
        self._weekday = match.group(1)  # weekday from heading
        self._week = match.group(2)     # week from heading
        self._cohort = match.group(3)   # cohort from heading

    def weekday(self):
        """Return weekday string."""
        return self._weekday
        
    def week(self):
        """Return week string."""
        return self._week

    def cohort(self):
        """Return cohort string."""
        return self._cohort

    def _is_cohort(self, cohort):
        """Return true if self._cohort contains cohort."""
        return cohort.upper() in self._cohort.upper()

    def isBHS(self): return self._is_cohort('BHS')
    def isRED(self): return self._is_cohort('RED')
    def isBLU(self): return self._is_cohort('BLU')

    def __str__(self):
        """Return string representation of Heading."""
        return f"{self.weekday()}|{self.week()}|{self.cohort()}"

    __repr__ = __str__

class Block:
    """Encodes data on schedule blocks."""

    def __init__(self, name, start, end, school, column, day, lunch):
        """Initialize schedule block class."""
        self._name = name               # block name
        self._start = start             # start minute
        self._end = end                 # end minute
        self._school = school           # which school cohort is at
        self._column = column           # column of _schedule
        self._day = day                 # day name
        self._lunch = lunch             # lunch name

    def name(self):
        """Return name string."""
        return self._name
        
    def start(self):
        """Return start minute."""
        return self._start

    def end(self):
        """Return end minute."""
        return self._end

    def school(self):
        """Return school on [None, 'BHS', 'OLS', 'PB2O', 'PO2B']."""
        return self._school

    def column(self):
        """Return column number."""
        return self._column

    def day(self):
        """Return day string."""
        return self._day

    def duration(self):
        """Return duration of this block."""
        return self._end - self._start + 1

    def _duration(self):
        """Return string for duration."""
        start = datetime.time(self._start // 60, self._start % 60) \
            .strftime('%I:%M')          # %p
        end = datetime.time((self._end + 1) // 60, (self._end + 1) % 60) \
            .strftime('%I:%M')          # %p
        return f"{start}-{end}"

    def lunch(self):
        """Return lunch string."""
        return self._lunch

    def __str__(self):
        """Return string representation of Block."""
        return f"{self._name}-" \
            f"{self._duration()}-" \
            f"{self.duration()}-" \
            f"{self._school}-" \
            f"({Heading(self._day)})-" \
            f"{self._lunch}-" \
            f"{self._column}"

    __repr__ = __str__

class Schedule:
    """2019-2020 BHS Schedule."""

    def __init__(self, csvfile, datadir='../data', wwwdir='../www'):
        """Initialize Schedule class for path .CSV file, including reading
        path .CSV file from datadir and writing path .HTML file to wwwdir."""
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
  <!--
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
        <h2>{filename} &mdash; {datetime}</h2>
        <article>
          <p>This file is available on <a href="https://github.com/psb-2018-2019-apcsp/bhs-calendar/">Github</a>&hellip;</p>
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
  <div class={bs}>
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
        self._init(csvfile, datadir, wwwdir)

    def _init(self, csvfile, datadir, wwwdir):
        """Initialize webpage parameters."""
        filename, extension = os.path.splitext(csvfile)
        self._filename, self._datadir, self._wwwdir = filename, datadir, wwwdir
        assert extension == '.csv', f"Bad extension: '{extension}' != '.csv'"

        self._schedule = \
            self.csv(os.path.join(self._datadir, self._filename + '.csv'))
        version = self._schedule[0][0]                  # which lunch version
        self._formatted_datetime = datetime.datetime.now().strftime('%c')
        # strftime('%a-%Y/%m/%d-%I:%M:%S%p%z')
        csv = ''
        for row in self._schedule:
            csv += f"{row}\n"
        self._comment = f"Created by {type(self).__name__} " \
            f"on {self._formatted_datetime} " \
            f"from CSV{':'} \n{csv}"
        self._dict = dict()

        pB2O, pO2B = 'PB2O'.upper(), 'PO2B'.upper()     # to check for school
        for col in range(1, max([ len(row) for row in self._schedule ])):
            blocks = list()
            day, name = self._schedule[0][col], self._schedule[1][col]

            firstB2O, lastB2O, firstO2B, lastO2B = None, None, None, None
            for row in self._schedule[1: ]:
                # Look for inter-school passing.
                if pB2O in row[col]:
                    if not firstB2O:
                        firstB2O = lastB2O = self._minute(row[0])
                    else:
                        lastB2O = self._minute(row[0])
                if pO2B in row[col]:
                    if not firstO2B:
                        firstO2B = lastO2B = self._minute(row[0])
                    else:
                        lastO2B = self._minute(row[0])

            start = end = self._minute(self._schedule[1][0])
            for row in self._schedule[1: ]:
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
                        school = name if pB2O in name or pO2B in name else \
                            'OLS' if \
                                ('RED' in day.upper() and \
                                    (lastB2O == None or start > lastB2O)) or \
                                ('BLUE' in day.upper() and \
                                    (firstO2B == None or end < firstO2B)) \
                            else 'BHS'
                        block = Block(name, start, end, school, col, day, version)
                        blocks.append(block)
                    name = row[col]
                    start = end = self._minute(row[0])
            self._dict[day] = blocks
        self.webpage(os.path.join(self._wwwdir, self._filename + '.html'))

    # ///////////////////////////// UTILITIES //////////////////////////////

    def _minute(self, time):
        """Return minute number for time string, e.g. '7:30 AM' yields 450."""
        parsed = datetime.datetime.strptime(time, '%I:%M %p')
        return parsed.hour * 60 + parsed.minute

    def _wrap(self, text, indent=0, wrap=80, delimiter=' '):
        """Return text, broken into lines of no more than wrap characters,
        indented by indent spaces. Indent only, if wrap <= 0."""
        length, start, last, space, result = wrap - indent, 0, 0, ' ', ''
        for i, c in enumerate(text.strip()):
            if length > 0 and i - start >= length:
                result += '\n' + space * indent + text[start: last]
                start = last
            if c == delimiter:
                last = i + 1
            if c == '\n':
                result += '\n' + space * indent + text[start: i]
                start = last = i + 1
        result += '\n' + space * indent + text.strip()[start: ]
        return result[1: ]

    def webpage(self, outpath=None):
        """Create self.page and save in outpath (or print if None)."""
        scale = lambda x: round(x * 3, 0)
        days = ''
        # Process every column, keeping three cohorts together for every day.
        for i, key in enumerate(self._schedule[0][1: ]):
            if i % 3 == 0:                              # start of a new day
                cohorts = ''
            head = Heading(key)
            column = f"{head.weekday()} - {head.week()}"
            style = f"blocks"
            cohort = head.cohort()
            # Add skip to empty paragraph for empty block at start of day.
            skip = scale(self._dict[key][0].start()
                - self._minute(self._schedule[1][0]))
            skip += 2 if skip else 0                    # adjust for border(s)
            blocks = f"""    <p class="start" style="height: {skip}px;"></p>\n"""
            # Add a paragraph for every block to cohort.
            for block in self._dict[key]:
                name = block.name().upper()
                is_passing = name[0] in [ 'P', '?', ]
                is_passing_split = name in [ 'PS', ]
                is_passing_question = name in [ '?' ]
                is_school_passing = name in [ 'PB2O', 'PO2B', ]
                # Display passing blocks w/ no content, just mouse-over title.
                if is_passing and not is_school_passing:
                    cls = f"passing"
                    text = ''
                    if is_passing_split:
                        cls += f" split"
                    if is_passing_question:
                        cls += f" question"
                    if block.duration() < 5:
                        cls += f" short"
                else:
                    school = block.school()
                    cls = f"school-{name.lower()}" \
                        if is_school_passing \
                        else f"block cohort-{cohort.lower()} " \
                            f"school-{school.lower()}"
                    text = f"{block.name()}<br />" \
                        f"{block._duration()}<br />" \
                        f"{block.duration()}"
                    if name[0] in [ 'L', ]:             # add lunch class
                        cls += f" lunch"
                pad = scale(block.duration())
                title = f"{name} @ " \
                    f"{school}: " \
                    f"{block._duration()} = " \
                    f"{block.duration()}"
                blocks += self._wrap(self._block_format.strip().format(
                    cls=cls, pad=pad, title=title, text=text),
                        4, 0) + '\n'
            cohorts += self._wrap(self._blocks_format.strip().format(
                bs=style, cohort=cohort, blocks=blocks.rstrip()), 4, 0) + '\n'
            if i % 3 == 2:                              # end of cohort
                days += self._wrap(self._cohorts_format.strip().format(
                    column=column, cohorts=cohorts.rstrip()), 2, 0) + '\n'

        # Calculate totals for each block for each cohort.
        names = set()
        for key in self._dict.keys():
            names.add(Heading(key).cohort())
        names = [ 'BHS', 'Red', 'Blue', ]               # need this order
        totals = dict()
        for name in names:
            totals[name] = dict()
            for key, blocks in self._dict.items():
                for block in blocks:
                    # Match block letter(s) followed by number(s).
                    match = re.match(r'(\D+)\d+$', block.name())
                    if Heading(block.day()).cohort() == name and match:
                        c = match.group(1)
                        totals[name][c] = \
                            totals[name].get(c, 0) + block.duration()
                    # Handle lunches separately.
                    if block.name().upper()[0] == 'L':
                        totals[name]['L'] = \
                            totals[name].get('L', 0) + block.duration() 
        """
        # ECHO TOTALS
        for c, t in totals.items():
            print(c, ':', end = ' ')
            s = ''
            for k in sorted(t.keys()):
                s += f"{k}={t[k]} "
            print(s)
        """
        # Add cohort columns for totals.
        column = 'Totals'
        cohorts = ''
        style = f"totals"
        keys = set([ k for n in names for k in totals[n].keys() ])
        for cohort in names:
            blocks = ''
            for key in sorted(keys):
                cls = 'total'
                title = text = f"{key} = {totals[cohort].get(key, 0):03d}"
                blocks += self._wrap(self._total_format.strip().format(
                    cls=cls, title=title, text=text),
                            4, 0) + '\n'        
            cohorts += self._wrap(self._blocks_format.strip().format(
                bs=style, cohort=cohort, blocks=blocks.rstrip()), 4, 0) + '\n'

        days += self._wrap(self._cohorts_format.strip().format(
            column=column, cohorts=cohorts.rstrip()), 2, 0) + '\n'

        # Format <main>.
        main = self._wrap(self._days_format.strip().format(
            days=days.rstrip()), 6, 0)

        # Format webpage.
        heading = f"{self._schedule[0][0]} Lunch"
        comment = self._wrap(self._comment, 4, 0)
        filename = self._filename
        datetime = self._formatted_datetime
        self.page = self._webpage_format.strip().format(
            comment=comment, heading=heading, main=main,
            filename=filename, datetime=datetime)

        # Write or print self.code.
        if outpath:
            with open(outpath, 'w') as outfile:
                outfile.write(self.page)
            print(outpath)
        else:
            print(self.page)

    def csv(self, csvpath):
        """Return csv file as 2d list."""
        with open(csvpath) as csvfile:
            schedule, schedulereader = list(), csv.reader(csvfile)
            for row in schedulereader:
                schedule.append(row)
        return schedule

if __name__ == '__main__':
    if 'idlelib' in sys.modules:
        human_schedule = Schedule('schedule-1b-bhs-2019-2020-human.csv')
        steam_schedule = Schedule('schedule-1b-bhs-2019-2020-steam.csv')

##        print(Block('FOO', 100, 199, 'BHS', 47, 'BAR BLAP FRAB', 'STEAM'))
##
##        lipsum = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Quisque viverra ex vitae nisi volutpat, vitae elementum felis eleifend. Nullam laoreet ac nisl a dignissim. In sem libero, gravida commodo diam eu, egestas vehicula purus. Pellentesque laoreet maximus nunc, eget sollicitudin urna feugiat id. Sed aliquam purus ut leo pellentesque, euismod eleifend quam eleifend. Pellentesque eget urna sed nisl finibus facilisis. Aliquam consequat diam magna, in mollis leo posuere imperdiet. Ut fermentum bibendum pellentesque. Aenean eleifend massa nisi, et dictum justo sagittis id. Etiam sollicitudin et turpis at cursus. Proin nec est lectus. Nullam dui purus, imperdiet a mattis in, convallis dictum massa. Suspendisse nec fringilla nibh.
##
##Quisque a purus et purus mattis venenatis non at tellus. Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Nullam tincidunt tincidunt bibendum. Fusce interdum lacus eu ex tincidunt auctor. Vestibulum efficitur libero sem, eu viverra est finibus vitae. Vivamus viverra imperdiet euismod. Fusce neque eros, vehicula ut leo aliquam, efficitur vestibulum velit.
##
##Duis accumsan hendrerit leo non placerat. Donec pretium eros urna, in semper neque venenatis a. In hac habitasse platea dictumst. Mauris pharetra tellus purus, et ultrices neque feugiat quis. Donec sagittis rutrum ipsum, nec condimentum augue malesuada vitae. Fusce ornare cursus quam, et sollicitudin purus varius ac. Proin velit nunc, dictum sit amet purus nec, facilisis eleifend turpis. Cras at dui gravida dolor elementum congue in luctus magna. Pellentesque in eros et nibh lacinia luctus. Etiam finibus lacus ut imperdiet facilisis. Nulla facilisi. Etiam ac augue at dolor placerat aliquet. Morbi sit amet pellentesque libero. Etiam ante magna, mollis nec viverra vitae, consectetur ac dui.
##
##""".replace(' ', ' ')
##        print('1234567890' * 9)
##        print('"{}"'.format(schedule._wrap(lipsum, 4)))