"""
This module deals with dump exporting and handling activites
"""

import requests, os
from bs4 import BeautifulSoup

from .export_releasedata import ExportReleaseData

class DumpScraper(ExportReleaseData):

    def __init__(self):
        super().__init__()
        self.web_report = 'web_app_prod_report'
        self.db_report = 'db_prod_report'
        self.config_report = "minimal"
        self.testrail_email=self.config[self.testrail]["user_email"]
        self.testrail_password=self.config[self.testrail]["user_pass"]
        self.testrail_login_url=self.config[self.testrail]["testrail_login_url"]
        self.testrail_milestone_url=self.config[self.testrail]["testrail_milestone_url"]
        self.testrail_export_milestone_url=self.config[self.testrail]["testrail_export_milestone_url"]
        self.testrail_export_plan_url=self.config[self.testrail]["testrail_export_plan_url"]
        self.testrail_export_run_url=self.config[self.testrail]["testrail_export_run_url"]

    def _get_required_columns(self, report_format):
        """
        Customized Columns for dumps

        :return: dump columns
        """
        self.required_fields=""
        self.required_path = "csv_exports"
        if report_format=="all_cols":
            self.required_fields='tests:id,cases:title,tests:title,tests:assignedto_id,' \
                                  'tests:case_id,tests:original_case_id,tests:comment,tests:defects,' \
                                  'tests:custom_failed,cases:custom_label,cases:milestone_id,' \
                                  'tests:plan_name,tests:plan_id,tests:run_name,tests:run_id,' \
                                  'cases:section_id,tests:status_id,tests:tested_by,tests:tested_on,' \
                                  'tests:version,cases:section_full,cases:type_id'
        elif report_format==self.config_report:
            self.required_fields='cases:title,tests:run_name,' \
                                'tests:status_id,tests:tested_by,tests:tested_on'
        elif report_format==self.db_report:
            self.required_fields='tests:run_name,tests:status_id,tests:tested_by,tests:tested_on'
        elif report_format==self.web_report:
            self.required_fields='tests:run_name,tests:status_id,tests:tested_by,tests:tested_on'
            self.required_path = 'web_app_exports'
        elif report_format=="bug_report":
            self.required_fields='tests:id,cases:title,tests:title,tests:assignedto_id,tests:case_id,' \
                                  'tests:original_case_id,tests:comment,tests:defects,tests:custom_failed,' \
                                  'cases:custom_label,cases:milestone_id,cases:section_id,tests:status_id,' \
                                  'tests:tested_by,tests:tested_on,tests:version,cases:section_full'
        elif report_format=="case_report":
            self.required_fields='tests:id,cases:title,tests:title,tests:assignedto_id,tests:case_id,' \
                                  'tests:original_case_id,tests:comment,tests:defects,tests:custom_failed,' \
                                  'cases:custom_label,cases:milestone_id,tests:plan_name,tests:plan_id,' \
                                  'cases:section_id,tests:status_id,tests:tested_by,tests:tested_on,' \
                                  'tests:run_name,tests:run_id,tests:version,cases:section_full'
        elif report_format=="org_prod":
            self.required_fields='tests:id,cases:title,tests:title,tests:assignedto_id,tests:case_id,' \
                                  'tests:original_case_id,tests:comment,tests:defects,tests:custom_failed,' \
                                  'cases:custom_label,cases:milestone_id,tests:plan_name,tests:plan_id,' \
                                  'tests:run_name,tests:run_id,cases:section_id,tests:status_id,' \
                                  'tests:tested_by,tests:tested_on,tests:version,cases:section_full'
        else:
            self.log.error("Wrong Input in Report Format, Please try giving below formats alone\n"
                          "* all-cols\n* minimal \n* prod_report\n* bug_report\n"
                          "* case_report\n* org_prod \n")
            raise SystemExit
        return self.required_fields, self.required_path

    def export_csv_with_export_type(self, rid, export_type, report_type):
        """
        web scrapes or fetches the html content of requested milestones

        :param rid: int value of release_id
        :param export_type: release type to define wether export is milestone / run / plan
        :param report_type: type of report to export , i.e prod / bug / case
        :return: path of the milestone exported
        """
        self.dump_columns, self.dump_path = self._get_required_columns(report_type)
        session=requests.Session()
        payload={
            'name': self.testrail_email,
            'password': self.testrail_password,
            'rememberme': '1'
        }
        # login and get csrf token
        session.get(self.testrail_login_url)
        self.log.info("session_response=>%s",session.post(self.testrail_login_url, data=payload))

        """ got using background url found in form action of the milestone using f12 hotkey"""
        page_content=session.get(self.testrail_milestone_url.format(rid)).content
        soup=BeautifulSoup(page_content, features='html.parser')
        csrftoken=soup.find('input', dict(name='_token'))['value']

        # csv export
        session.post(self.testrail_login_url, data=payload)
        payload={
            '_token': csrftoken,
            'columns': self.dump_columns,
            'format': 'csv',
            'layout': 'tests',
            'section_ids': '',
            'section_include': '',
            'separator_hint': '1'
        }
        if export_type=="milestone":
            export=session.post(self.testrail_export_milestone_url.format(rid), data=payload).content
            path=os.getcwd() + '/{}/{}.csv'.format(self.dump_path, rid)
            with open (path, 'wb')as new:
                new.write(export)
            return path
        elif export_type=="plan":
            export = session.post(self.testrail_export_plan_url.format(rid), data=payload).content
            path = os.getcwd() + '/{}/{}.csv'.format(self.dump_path, rid)
            with open (path, 'wb')as new:
                new.write(export)
            return path
        elif export_type=="run":
            export = session.post(self.testrail_export_run_url.format(rid), data=payload).content
            path = os.getcwd() + '/{}/{}.csv'.format(self.dump_path, rid)
            with open (path, 'wb')as new:
                new.write(export)
            return path

    def _get_chunk_count(self, lst, split_count):
        """
        gets the list of available chunks in a list

        :param lst: list of chunks
        :param split_count: number of chunks to split equally
        :return: list of chunks with release id's
        """
        for items in range(0, len(lst), split_count):
            yield lst[items:items + split_count]

    def _split_list_evenly_to_files(self, fil_dir, file_lst, split_into=30):
        """
        splits the provided file with n number of releases 
        into n number of parts based on user choice equally

        :param file_dir: directory to store
        :param file_lst: list of files with release id's
        :param split_into: number of parts the release id needs to  be split
        """
        lst = list(self._get_chunk_count(file_lst, split_into))
        count=0
        for release_ids in lst:
            count+=1
            with open('{0}dump_{1}.txt'.format(fil_dir, count), 'w') as release_file:
                for rid in release_ids[0:-1]:
                    release_file.write(str(rid)+ '\n')
        self.log.info("No of files split into => %s",count)

    def split_num(self, number, parts):
        """
        splits a provided number into equal parts

        :param number: number to split
        :param parts: number of parts to split equally
        """
        filepart=[number //parts + (1 if x < number % parts else 0) for x in range(parts)]
        self.log.info(filepart)

    def _clean_directory(self, file_dir):
        """
        cleans test dumps which are exported

        :param file_dir: file directory to clean or empty
        """
        for item in file_dir:
            for file_value in os.listdir(item):
                self.log.info("Deleting => %s %s files", item,file_value)
                os.remove("{}/{}".format(item,file_value))


#a=DumpScraper()
#to export releses
# a.export_csv_with_export_type(26805, 'milestone', 'case_report')
#to split files
# with open('{}.txt'.format('filename'), 'r') as r:    
    # splitter_list = [rid.rstrip('\n') for rid in r]
    # a._split_list_evenly_to_files(splitter_list, split_into=100)
# TODO 
# function to export splited files with release type [ testrail scraper]
#  runs_list = []
#     plans_list = []
#     m_list = []
#     user_choice = input("enter dump choice \n  runs \n plans \n milestones \n")
#     file_name = input("enter file_name : ")
# if user_choice == "runs":
#         with open('{}.txt'.format(file_name), 'r') as r:
#             for data in r:
#                 temp = data.rstrip('\n')
#                 count += 1
#                 runs_list.append(temp)
#         # split_num(count, 5)
#         export_run_or_plan(user_choice, runs_list)
#     elif user_choice == "plans":
#         with open('{}.txt'.format(file_name), 'r') as p:
#             for data in p:
#                 temp = data.rstrip('\n')
#                 plans_list.append(temp)
#         export_run_or_plan(user_choice, plans_list)
#     else:
#         print("wrong choice")
#         exit
    
#     if user_choice == "milestones":
#         with open('{}.txt'.format(file_name), 'r') as m_file:
#             for data in m_file:
#                 temp = data.rstrip('\n')
#                 m_list.append(temp)
#         export_run_or_plan(user_choice, m_list)
    

#     print (len(runs_list),'runs', len(plans_list),'plans', len(m_list),'milestones')
