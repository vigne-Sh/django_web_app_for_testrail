"""
This module deals with loggin base for entire tool
"""

import os, sys, coloredlogs, logging
import re
from datetime import date, datetime, timedelta

class LoggerBase:

    def __init__(self):
        
        logging.basicConfig(level=logging.DEBUG,
                            format='%(levelname)s: [%(asctime)s] %(message)s',
                            datefmt='%d/%B/%Y %I:%M:%S %p')
        self.log=logging.getLogger(__name__)
        coloredlogs.install(fmt='[%(asctime)s] %(hostname)s %(levelname)s:'
                            '%(name)s[%(process)d] [%(module)s.%(funcName)s]'
                            '%(message)s', datefmt="%d/%B/%Y %I:%M:%S %p",
                            level='INFO', logger=self.log)
        #to debug use DEBUG parameter in above level
        self.timeformat='%-m/%-d/%Y'
        self.prod_format='%d/%m/%Y'
        self.sprint_timeformat='%B/%-d/%Y'

    def _get_exact_time(self):
        """
        get the exact time to trigger report based on requirement

        :return: exact time GST
        """
        current_time = datetime.now().strftime("%H:%M")
        return current_time

    def _get_todays_date(self):
        """
        get todays's date to generate report based on timelines

        :return: todays date
        """
        running_platform = sys.platform
        if "win32" in running_platform:
            today = datetime.today().strftime("%#m/%#d/%Y")  # today's date without leading zero
        elif "linux" or "darwin" in running_platform:
            today = datetime.today().strftime("%-m/%-d/%Y")  # today's date without leading zero
        return today

    def _get_weekly_dates(self, time_range=7, format_of_time='report'):
        """
        get weekly dates to generate report based on timelines

        :return: weeks date
        """
        if format_of_time=='mail':
            format_of_time=self.sprint_timeformat
        elif format_of_time=='report':
            format_of_time=self.timeformat
        else:
            self.log.error("Wrong Time format Either use report / mail")
            raise SystemExit
        date_list = []
        end = datetime.today()
        start=end - timedelta(days=time_range)
        end_date=end.strftime(format_of_time)
        start_date=start.strftime(format_of_time)
        for i in range(time_range):
            e=end - timedelta(days=i)
            date_list.append(e.strftime(format_of_time))
        return date_list

    def _get_explode_values(self, release_length=2):
        """
        get pie chart list values for explode based on release count

        :return: exploded_list
        """
        initial_explode = 0.2
        item_length = 0
        explode_list = [item_length for _ in range(release_length-1)]
        explode_list.insert(0, initial_explode)
        return explode_list

    def _get_date(self):
        date_entry = input('Enter a date in YYYY-MM-DD format')
        year, month, day = map(int, date_entry.split('-'))
        return date(year, month, day)

    def daterange(self, d1, d2):
        return (d1 + timedelta(days = i) for i in range(( d2 - d1).days + 1))

    def _get_date_with_format(self, timeformat, date_format='jira'):
        if date_format == 'jira':
            return datetime.today().strftime(timeformat)
