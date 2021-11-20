
from datetime import datetime
import re, sys, os, subprocess
import pandas as pd
import numpy as np
from glob import glob
import matplotlib.pyplot as plt

from .transporter.dump_scraper_client import DumpScraper
from .report_constructor.helpers.images import *

class PRODException(Exception):
    pass


class ReportBase(DumpScraper):
    """
    Base for every type of PROD Report
    """
    def __init__(self):
        super().__init__()
        self.prod_exception = PRODException
        self.today=self._get_todays_date()
        self.trigger_time=self._get_exact_time()
        self.weekly_dates=self._get_weekly_dates()
        self.color_dict = {'Passed': '#10bb35',
                            'Blocked' : '#5215c5',
                            'Retest' : '#fcff47',
                            'Failed' : '#ff1d1d',
                            'Caution' : '#f05a1e',
                            'Skipped' : '#666256',
                            'Performance' : '#289fd6',
                            'Queried' : '#d80deb',
                            'Parked' :  '#11f8f8',
                            'Running' :  '#1121f8',
                            'Not Applicable' : '#000000',
                            'Untested' : '#a4d8cda6'
                         }
        self.playback_list=["Validate Playback", "Validate Playback (4K)", "Validate Playback [VOD]"]
        self.sent_from="FireTV PROD bot <FireTV_Prod_Report@amazon.com>"
        self.mail_subject="[{team_name} Productivity Report] - Testrail / JIRA PROD for {team_name} Team members"
        self.subject_ndl="Productivity Report - Daily Case Execution by Team members."
        self.pie_color= ['#ff870f', '#ceed66', '#ff4d94', '#339966', '#00ff00', '#0080ff', '#ffff00', '#00ffff', '#975008',
                         '#ec145c', '#f5739e', '#7cff25', '#0a1f7a', '#d365f5', '#8d1a6a', '#cab019', '#7c0000']
        self.supported_teams=["3p", "sdl", "sysapps", "ftve_kamino", "vizzini",
                                "ndl_program", "voice", "smart_tv_kaine_juliana",
                                "remotes_team", "bison", "ftv_integration",
                                "ftv_ndl_integration", "ftv_shenzhen", "launcher",
                                "gordon", "laguna_pqa", "firetv_eu_us"]
        self.prod_report_required_fields=['Tested By', 'Tested On', 'Status','Run']
        self.milestone_progress_image = 'rdata.png'
        self.release_status_image = "regression_status.png"
        self.regression_time_heatmap = "regression_timemap.png"
        self.thanks_logo_image_name = "az_logo"
        self.thanks_border_image_name = "thanks_border"
        self.logo_image = 'raptr/static/images/az_logo.png'
        self.thanks_border_image = 'raptr/static/images/thanks_border.gif'
        self.files={
                    'files': {
                            'run_files': 'runs.txt',
                            'plan_files': 'plans.txt',
                            'run_milestones' : 'milestones_r.txt',
                            'plan_milestones' : 'milestones_p.txt',
                            },
                    'directory':{
                                    'root_dir': 'csv_exports/',
                                    'prod_dir': 'productivity_db/root_dump',
                                    'run_dir': 'temp/runs/',
                                    'plan_dir': 'temp/plans/',
                                    'milestone_dir': 'temp/milestones/',
                                },
                    'csv_format': '*.csv'
                    }
        self.jira_url = "https://issues.labcollab.net/issues/?jql="
        self.jira_filter_date_format = "%Y-%m-%d"
        self.today_issues = "reporter in ({user_id_list}) AND createdDate >= {created_date}"
        self.today_blocker_issues = "reporter in ({user_id_list}) AND createdDate >= {created_date} AND priority = Blocker"

    ###################
    ###Export##########
    ###################
    """"
    Exports related Functions
    """

    def _get_run_time(self):
        return '3'

    def _get_release_status_color(self, release_dump):
        if release_dump.empty:
            return '#38ec13'
        else:
            return '#f70000'

    def _get_project_name(self, project_list):
        return list(map(self.project_dict.get, project_list))

    def _get_dump(self, release_id, release_type, report_type):
        """
        get testrail export for requested release

        :param release_id: release id of the release
        :param release_type: release type of release i.e, milestone / run / plan
        :param report_type: report type to export columns accordingly
        """
        return self.export_csv_with_export_type(release_id, release_type, report_type)

    def pull_exports(self, export_list, export_type, report_type):
        """
        exports multiple dumps
        """
        for release_ids in export_list:
            self.export_csv_with_export_type(release_ids, export_type, report_type)

    def _read_export(self, export_id, report_type=None):
        """
        read's csv export

        :param export_id: release id
        :return: returns exported csv dump
        """
        self.log.info("Reading Exports for Report type:  %s", report_type)
        export_columns, export_path = self._get_required_columns(report_type)
        df=pd.read_csv("{}/{}.csv".format(export_path, export_id))
        return df

    def ignore_case(self, pattern):
        """
        ignore file matching pattern if any format found

        :return: list of file path
        """
        try:
            return ''.join((f'[{c.lower()}{c.upper()}]' if c.isalpha() else c for c in pattern))
        except Exception as e:
            self.log.error("Exception in ignore case patter: %s", e)

    def multi_glob(self, patterns):
        """
        reads mutliple file paths

        :return: yielded glob paths
        """
        try:
            for path, pattern in patterns:
                yield from glob(os.path.join(path, self.ignore_case(pattern)))
        except Exception as e:
            self.log.error("Exception in multi glob: %s", e)

    def merge_csv_files(self, is_default_dir=1, get_chart=False, valid_release_count=False):
        """
        merge all available dumps that are exported

        # input => list(multi_glob((("productivity_db/milestones/", "*.csv"),
        #                           ("productivity_db/runs/","*.csv"),
        #                           ("productivity_db/plans/","*.csv"))))
        :return: merged csv dump
        """
        if not is_default_dir:
            file_path = list(self.multi_glob((("productivity_db/milestones/", self.files['csv_format']),
                                              ("productivity_db/runs/", self.files['csv_format']),
                                              ("productivity_db/plans/", self.files['csv_format']))))
        else:
            file_path = glob("csv_exports/*.csv")
        self.log.info("Files fetched [%s]: %s", len(file_path), file_path)
        csv_x=(pd.read_csv(f) for f in file_path)
        if len(file_path):
            csv_x=pd.concat(csv_x, ignore_index=True, sort=True)
            if get_chart:
                self.log.info("Generating Release Based Status Chart from dumps")
                self._get_release_status_chart(testrail_pie_dump=csv_x, release_count=len(file_path), chart_type='pie')
                self.log.info("Getting Time based  heat map Chart from dumps")
                self._get_time_heatmap(testrail_dump=csv_x, release_count=len(file_path))
        if valid_release_count:
            return csv_x, file_path
        else:
            return csv_x

    def _get_todays_dump(self, testrail_dump):
        """
        get dump with execution of today's date alone

        :return: today's dump
        """
        try:
            todays_df=testrail_dump[testrail_dump["Tested On"].str.contains(self.today, na=False)]
            return todays_df
        except Exception as e:
            self.log.error("EMPTY DF for today when merging")
            return 0

    def _get_head_count(self, testrail_dump):
        """
        get exact head count of resources worked in release

        :testrail_dump: dump of release
        :return: no of head_count
        """
        return len(testrail_dump['Tested By'].drop_duplicates())

    def _get_team_average(self, testrail_dump):
        """
        Get Average Count of team execution

        :param testrail_dump: testrail dump of team to fetch issues
        :return: team's average prod value
        """
        if testrail_dump.empty:
            self.log.error("NO average prod since empty dump")
            return len(testrail_dump)
        else:
            testrail_dump = testrail_dump['Tested By'].value_counts().rename_axis("Tested_User"). \
                            reset_index(name="Testcase_Count")
            return int(round(testrail_dump['Testcase_Count'].mean(), 0))

    def _get_jira_url(self, testrail_dump, issue_type='normal'):
        """
        get jirahref for jira issues

        :param testrail_dump: testrail dump of team to fetch issues
        :param issue_type: issue type either normal or blocker
        :return: list of amazon user id for the users who executed in testrail
        """
        if testrail_dump.empty:
            self.log.error("No jql to generate since empty dump")
            return self.jira_url
        else:
            issue_jql = ''
            if issue_type == 'blocker':
                issue_jql = self.today_blocker_issues
            elif issue_type == 'normal':
                issue_jql = self.today_issues
            return self.jira_url + issue_jql.format(user_id_list=','.join(self._get_amazon_user_id_list(testrail_dump=testrail_dump)),
                                                created_date = self._get_date_with_format(timeformat=self.jira_filter_date_format))

    def _get_amazon_user_id_list(self, testrail_dump):
        """
        get amazon user id from testrail dump

        :return: list of amazon user id for the users who executed in testrail
        """
        empty_df = pd.DataFrame()
        if testrail_dump.empty:
            self.log.error("NO user_id fetched since empty dump")
            return empty_df
        else:
            static_ldap_testrail_export = pd.read_csv("final_emp_details.csv")
            testrail_users_list = testrail_dump["Tested By"].drop_duplicates().dropna().to_list()
            static_ldap_testrail_export = static_ldap_testrail_export[["user_id", "testrail_username"]]
            static_ldap_testrail_export = static_ldap_testrail_export[static_ldap_testrail_export["testrail_username"]. \
                                          str.contains("|".join(testrail_users_list), na=False)]
        return static_ldap_testrail_export['user_id'].to_list() if len(static_ldap_testrail_export) else empty_df

    def _get_jira_issues(self, testrail_dump, issue_type='normal'):
        """
        get list of issues raised by employees during execution

        :param testrail_dump: testrail dump of team to fetch issues
        :param issue_type: issue type either normal or blocker
        :return: list of jira issue keys
        """
        issue_keys = []
        if testrail_dump.empty:
            self.log.error("No %s issues fetched since empty dump", issue_type)
        else:
            if issue_type == 'blocker':
                issue_keys = self.jira_client.search_issues(self.today_blocker_issues.format(
                                                            user_id_list=','.join(self._get_amazon_user_id_list(testrail_dump=testrail_dump)),
                                                            created_date = self._get_date_with_format(timeformat=self.jira_filter_date_format)),
                                                            maxResults=2000)
            elif issue_type == 'normal':
                issue_keys = self.jira_client.search_issues(self.today_issues.format(
                                                            user_id_list=','.join(self._get_amazon_user_id_list(testrail_dump=testrail_dump)),
                                                            created_date = self._get_date_with_format(timeformat=self.jira_filter_date_format)),
                                                            maxResults=2000)
        return [jira_issue.key for jira_issue in issue_keys] if issue_keys else []

    def filter_by_today_df(self, export_id, report_type = None):
        """
        filters if empty release is observed and return total count as 0

        :param export_id: release id to validate
        :param report_type: report type i.e bug / prod / minimal ..etc
        :return: release executed count
        """
        try:
            self.log.info("filtering data for %s id having report_type => is %s", export_id, report_type)
            release_df=self._read_export(export_id, report_type= report_type)
            release_df=release_df[release_df["Tested On"].str.contains(self.today, na=False)]
            return len(release_df) if len(release_df) else 0
        except:
            self.log.warning("NO export file observed for dump [%s]", export_id)
            return 0

    def filter_into_list(self, dict_or_list):
        """
        yields the values alone if nested in list of dicts, lists

        :return: list of values
        """
        if isinstance(dict_or_list, dict):
            for values in dict_or_list.values():
                yield from self.filter_into_list(values)
        elif isinstance(dict_or_list, list):
            for values in dict_or_list:
                yield from self.filter_into_list(values)
        else:
            yield dict_or_list

    def get_prod_team_summary(self):
        testrail_dump, release_list = self.merge_csv_files(get_chart=True, valid_release_count=True)
        today_dump = self._get_todays_dump(testrail_dump=testrail_dump)
        team_status_color = self._get_release_status_color(today_dump)
        no_of_case_count = len(today_dump)
        no_of_relases_count = len(release_list)
        head_count = self._get_head_count(today_dump)
        run_time = self._get_run_time()
        normal_jira_issues = self._get_jira_issues(testrail_dump=today_dump, issue_type='normal')
        normal_jira_issues_jql = self._get_jira_url(testrail_dump=today_dump, issue_type='normal')
        blocker_issues = self._get_jira_issues(testrail_dump=today_dump, issue_type='blocker')
        blocker_issues_jql = self._get_jira_url(testrail_dump=today_dump, issue_type='blocker')
        team_average_value = self._get_team_average(testrail_dump=today_dump)
        self.log.error("PROD SuMmARY =>\nfull_dump: %s \ndump_files: %s \ntodays_dump:%s" \
                       "\nteam_status:%s \nno_of_case:%s \nrelease_count:%s" \
                        "\nhead_count: %s \nrun_time: %s \nnormal_issues: %s \nnormal_jql: %s" \
                        "\nblocker_issues:%s \nblocker_jql:%s \nteam_avg_prod:%s",
                        testrail_dump.empty, len(release_list), today_dump.empty, team_status_color,
                        no_of_case_count, no_of_relases_count, head_count, run_time,
                        len(normal_jira_issues), normal_jira_issues_jql, len(blocker_issues), blocker_issues_jql,
                        team_average_value)
        return team_status_color, no_of_case_count, no_of_relases_count, head_count, run_time, \
               normal_jira_issues, normal_jira_issues_jql, blocker_issues, blocker_issues_jql, team_average_value

    def check_empty_df(self, export_dict, report_type):
        """
        checks if a df is empty or not and retunrs the filtered export list

        :param type: prod_report dictionary or web_app_prod_report dictionary
        :return: export_list with executed cases
        """
        self.log.info("Validating EMPTY DF for export_dict: [%s], \n" \
                      "with report_type = %s", export_dict, report_type)
        columns, dump_path = self._get_required_columns(report_type)
        export_list=[]
        filtered_export_list=[]
        if report_type == self.web_report:
            export_list=list(self.filter_into_list(export_dict))
        elif report_type == self.db_report:
            export_list=export_dict["releaseid"]
        elif report_type == self.config_report:
            export_list = list(self.filter_into_list(export_dict))
        self.log.info("Exports to parse by df: %s", export_list)
        for release in export_list:
            try:
                df=pd.read_csv("{}/{}.csv".format(dump_path, release))
                if len(df[df["Status"] == "Untested"]) != len(df):
                    filtered_export_list.append(release)
                else:
                    self.log.warning("EMPTY DF [%s]", release)
                    self._delete_dump(dump_path, release)
            except:
                self.log.error("NO FILE Found for dump [%s]", release)
                return filtered_export_list, dump_path
        self.log.info("Filtered Export List: [%s] dumps => %s ", len(filtered_export_list), filtered_export_list)
        return filtered_export_list, dump_path

    def _get_release_wise_count(self, export_dump, report_type):
        """
        get release wise name from testrail api

        :param export_dump: export dump of releases
        :param report_type: report type for getting columns
        :return: release names in html table
        """
        release_dict=export_dump
        release_name_list=[]
        release_id_list=[]
        release_length=[]
        release_project_list = []
        self.log.info("Getting Release wise count for dump %s \n" \
                        "having report_type => %s", export_dump, self.db_report)
        if len(release_dict):
            for rtype, rid in zip(release_dict["releasetype"], release_dict["releaseid"]):
                is_execution_done = self.filter_by_today_df(rid, report_type)
                if (rtype == "milestone") and is_execution_done:
                    release_name, release_project =self._get_release_and_project_name_(rtype=rtype, rid=rid)
                    release_name_list.append(release_name)
                    release_project_list.append(release_project)
                    release_id_list.append(rid)
                    release_length.append(is_execution_done)
                elif (rtype == "plan") and is_execution_done:
                    release_name, release_project =self._get_release_and_project_name_(rtype=rtype, rid=rid)
                    release_name_list.append(release_name)
                    release_project_list.append(release_project)
                    release_id_list.append(rid)
                    release_length.append(is_execution_done)
                elif (rtype == "run") and is_execution_done:
                    release_name, release_project =self._get_release_and_project_name_(rtype=rtype, rid=rid)
                    release_name_list.append(release_name)
                    release_project_list.append(release_project)
                    release_id_list.append(rid)
                    release_length.append(is_execution_done)
            self.log.info("[Release Data] %s releases, %s, %s", len(release_name_list), release_name_list, release_id_list)
            release_data=pd.DataFrame({"Release_ID": release_id_list, "Release_Name": release_name_list, "Total_Case_count": release_length})
            ax=release_data.plot(labels=release_data["Release_Name"], kind="pie", y="Total_Case_count")
            ax.set_title("Milestone Progress", weight="bold")
            ax.set_xlabel("MILESTONES")
            ax.set_ylabel(" ") 
            plt.legend(title="Case_count", labels=release_data["Total_Case_count"], bbox_to_anchor=(1.9,0.5), loc="lower right")
            plt.subplots_adjust(left=0.0, bottom=0.1, right=0.95)
            # plt.show() #-> to view each figure instantly while runtime
            fname="rdata.png"
            plt.savefig(fname, bbox_inches="tight")
            plt.close()
            release_data=release_data.rename(columns={'Case_count': 'Total_Case_count={}'.format(sum(release_length)) })
            self.log.info("Creating Release HTML file %s", len(release_data))
            release_html=release_data.to_html("html_exports/r_data.html",justify='center',index=False)
            if os.path.isfile("html_exports/r_data.html"):
                self.log.info("R data HTML File has been created for [%s] \n" \
                              "and verified..!!", export_dump)
            filtered_projects = self._get_project_name(list(set(release_project_list)))
            return filtered_projects if filtered_projects else []
        else:
            raise self.prod_exception("0 percent milestone progress detected")

    def get_qs_count_for_team(self, team_name, export_dict, report_type):
        read_csv=pd.DataFrame()
        self.log.info('Getting qs count for %s team having export: [%s]'\
                       'with report type => %s', team_name, export_dict, report_type)
        filtered_export_list, exports_path =self.check_empty_df(export_dict, report_type)
        for release_id in filtered_export_list:
            self.log.info("Generating PROD Report for [%s] release", release_id)
            read_csv=read_csv.append(pd.read_csv("{}/{}.csv".format(exports_path, release_id)))
        try:
            if len(read_csv):
                self.log.info("Processing Prod Table")
                read_csv=read_csv[(read_csv.Status != "Untested")]
                read_csv = read_csv[read_csv["Tested On"].str.contains(self.today, na=False)]
                qs_executed_date=[date.split(' ')[0] for date in read_csv["Tested On"]]
                read_csv["Tested On"] = qs_executed_date
                export_qs_data = read_csv
                add_playback_column = False
                if team_name == "3p":
                    export_qs_data=export_qs_data[["Tested By", "Title", "Tested On"]]
                    export_qs_data=export_qs_data[export_qs_data['Title'].str.contains("|".join(self.playback_list), na=False)]
                    qs_playback_count=export_qs_data.groupby(['Tested By']).size().reset_index(name ="Playback_Count")
                    
                    add_playback_column = True
                ####################
                #QS table creation
                ####################
                refined_csv=read_csv
                refined_csv=refined_csv[['Tested By', 'Status']]
                refined_csv=refined_csv.groupby(['Tested By', 'Status']).size().reset_index(name="Count")
                refined_csv=refined_csv.reset_index().groupby(['Tested By', 'Status'])['Count'].aggregate('first').unstack()
                refined_csv['Individual_Total']=refined_csv.sum(axis=1).astype(int)
                refined_csv.loc['Team_Total']=refined_csv.sum(axis=0)
                refined_csv.fillna(0, inplace=True)
                # refined_csv=refined_csv.astype('int32')
                refined_csv=refined_csv.round(decimals=0).astype(int)
                if add_playback_column:
                    refined_csv=pd.merge(refined_csv, qs_playback_count, on=["Tested By"], how="outer")
                    refined_csv.fillna(0, inplace=True)
                    refined_csv["Playback_Count"] = [int(x) for x in refined_csv["Playback_Count"]]
                if report_type != self.web_report:
                    qs_csv=refined_csv.to_csv("daily.csv", index=True) #-> create hard copy of instant report
                    if os.path.isfile("daily.csv"):
                        self.log.info("File created and found in path..!")
                    else:
                        self.log.warning("daily csv dump not found")
                        raise self.prod_exception("DUMP NOT Created")
                    if team_name == "3p":
                        refined_csv.reset_index(drop=True, inplace=True) #-> drop 0 ,1.. etc serial no
                        refined_csv.set_index("Tested By", inplace=True) #-> set tested users as index
                    refined_csv=refined_csv[refined_csv.columns[::-1]] #-> changing total count near to user name
                    refined_csv.index.name=None #-> drop empty void row space in index
                    refined_csv.columns.name="Tested By" #-> setting x,y empty space to user column heading
                    #to hard code file
                    qs_html=refined_csv.to_html("html_exports/qs_daily.html",justify='center',index=True)
                    if os.path.isfile("html_exports/qs_daily.html"):
                        self.log.info("HTML File has been created for %s export"\
                                        "and verified..!!", export_dict)
                return refined_csv.to_html(justify='center', index=True)
            elif report_type == self.web_report:
                self.log.error("Returning hTML exception")
                return ("<h1 id='user_update'> DUMPS deleted to clear cache, kindly generate new report </h1>")
        except Exception as e:
            raise PRODException("NO DUMPS To generate Report, add on-going releases ", e)

    def delete_exports(self, report_type):
        """
        remove all exports post sending report

        :param report_type: type of report which need to be deleted
        """
        self.log.info("Deleting exports for report_type %s", report_type)
        export_columns, export_path = self._get_required_columns(report_type)
        for files in os.listdir('html_exports/'):
            if ".log" in files:
                pass
            elif len(files):
                os.remove('html_exports/{}'.format(files))
        for files in os.listdir('{}/'.format(export_path)):
            if ".log" in files:
                pass
            elif len(files):
                os.remove('{}/{}'.format(export_path, files))
        if os.path.isfile('daily.csv'):
            os.remove('daily.csv')
        if os.path.isfile('rdata.png'):
            os.remove('rdata.png')
        self.log.info("DUMPS are Deleted .!")

    def _delete_dump(self, export_path, export_id):
        """
        remove exports that is not executed or progressed yet
        """
        if os.path.isfile('{}/{}.csv'.format(export_path, export_id)):
            os.remove('{}/{}.csv'.format(export_path, export_id))
            self.log.info("DUMP [%s.csv] Removed", export_id)

    def filter_duplicates(self, excel_dump): #todo yet to check on this
        fetch_dup=pd.concat(g for _, g in excel_dump.groupby("Case ID") if len(g) > 1)
        return fetch_dup

    def _merge_all_release_types(self):
        """
        reads all the individual csv dumps and consolidates the required fields into single file

        :return: csv dump
        """
        read_csv_milestone=glob("productivity_db/milestones/*.csv")
        df_from_each_csv_milestone=(pd.read_csv(f) for f in read_csv_milestone)
        concat_csv_m=pd.concat(df_from_each_csv_milestone, ignore_index=True, sort=True)

        read_csv_runs=glob("productivity_db/runs/*.csv")
        df_from_each_csv_run=(pd.read_csv(f) for f in read_csv_runs)
        concat_csv_1=pd.concat(df_from_each_csv_run, ignore_index=True, sort=True)

        read_csv_plans=glob("productivity_db/plans/*.csv")
        df_from_each_csv_plan=(pd.read_csv(f) for f in read_csv_plans)
        concat_csv_2=pd.concat(df_from_each_csv_plan, ignore_index=True, sort=True)

        concat_csv=pd.concat([concat_csv_1, concat_csv_2, concat_csv_m], ignore_index=True, sort=True)
        self.log.info(concat_csv)
        merged_csv_with_filter=self._required_fields_to_be_attached(self.prod_report_required_fields, concat_csv)
        self.log.info("HEAD COUNT %s", self._get_head_count(merged_csv_with_filter))
        merged_csv_with_filter.to_csv("productivity_db/final_csv/final_csv_{}.csv".format(self._get_exact_time()))
        return merged_csv_with_filter

    def _required_fields_to_be_attached(self, required_dump_fields, test_dump):
        """
        extracts the required fields from release dump

        :return: filtered csv dumps
        """
        test_dump=test_dump[required_dump_fields]
        test_dump=test_dump[test_dump.Status != "Untested"] #- > since we want the case split commenting this out from today data
        test_dump=test_dump[(test_dump['Tested By'] != "PQA Automation") | (test_dump['Tested By'] != "FTVI Automation")] #- > since we want the case split commenting this out from today data
        return test_dump

    ##################
    ##Chart Operation#
    ##################
    
    def _get_release_status_chart(self, testrail_pie_dump, release_count, chart_type='pie'):
        """
        Re-create testrail pie chart instance in form of pie / bar

        :param testrail_pie_dump: export dump to parse
        :param release_count: no of releases to create chart
        :param chart_type: type of chart to generate either = pie / bar
        :return: release status in form of .png pie / bar chart image
        """
        actual_df = testrail_pie_dump
        testrail_pie_dump=testrail_pie_dump.fillna({"Status":0})
        testrail_pie_dump = testrail_pie_dump.Status.value_counts().rename_axis('Status').reset_index(name='status_count')
        status_colors = testrail_pie_dump["Status"].map(self.color_dict)
        if chart_type == 'bar':
        #######
        ###bar chart for status
        #######
            testrail_pie_dump.plot(kind='bar', x='Status',
                             y='status_count', color=status_colors)
            plt.xticks(fontsize=7, rotation=31)
            plt.yticks(fontsize=7, rotation=25)
            plt.savefig(self.release_status_image, bbox_inches="tight")
            # plt.show()
        elif chart_type == 'pie':
         ########
        #        #
        #pie chart
         #       #
         #########
            testrail_pie_dump['percent_value'] = round((testrail_pie_dump['status_count']/len(actual_df)*100), 2)
            testrail_pie_dump['percent_value']= testrail_pie_dump['percent_value'].astype(str)
            temp = testrail_pie_dump
            temp['status_count'] = testrail_pie_dump['status_count'].astype(str)
            testrail_pie_dump['status_percent'] = testrail_pie_dump['Status'] + " - " + \
                                            testrail_pie_dump['percent_value']+ "%" + \
                                            " - " + temp['status_count'] + \
                                                "cases"
            plt.pie(x=testrail_pie_dump["status_count"],
                    colors=status_colors,
                    startangle=90, pctdistance=0.8)
            plt.title("CASE Execution Progress as of [{date}]".format(date=self._get_todays_date()),
                    pad=-0.1)
            plt.xticks(fontsize=7, rotation=31)
            plt.yticks(fontsize=7, rotation=25)
            plt.legend(labels=testrail_pie_dump['status_percent'],
                    title="[{case_count}] cases Executed for {release_count} Releases".format(case_count=len(actual_df),
                                                                                                release_count = release_count),
                        bbox_to_anchor=(1,0.1),loc="lower right", fontsize=7.4)
            plt.subplots_adjust(left=0.0, bottom=0.1, right=0.45)
            plt.tight_layout()
            plt.savefig(self.release_status_image, bbox_inches="tight")
            plt.close()
            # plt.show()
        else:
            raise self.prod_exception("Wrong chart type provided use either \n 'pie' \n 'bar'")

    def _get_time_heatmap(self, testrail_dump, release_count):
        """
        get time based heat map from testrail dump of tested users

        :param release_count: no of releases
        :param testrail_dump: dump to parse
        :retunr: chart representation of tested time of users in image
        """
        testrail_dump = testrail_dump[testrail_dump["Tested On"].str.contains(self.today,  na=False)]
        try:
            if not testrail_dump.empty:
                no_of_testers = len(testrail_dump["Tested By"].drop_duplicates().tolist())
                time_df  = testrail_dump["Tested On"].str.split(datetime.today().strftime("%Y"), 1, expand=True)[1]
                tester_df = testrail_dump["Tested By"]
                time_track_df = pd.DataFrame()
                time_track_df['tested_time'] = time_df
                time_track_df['tested_by'] = tester_df
                time_track_df['hours'] = time_track_df['tested_time'].str.split(":", 0, expand=True)[0]
                time_track_df['meridian'] = time_track_df['tested_time'].str.split(" ", 0, expand=True)[2]
                time_track_df['time_executed'] = time_track_df['hours'] + time_track_df['meridian']
                time_track_df.plot.scatter(x='time_executed', y='tested_by', color='#10bb35')
                plt.title("Execution Time Heat Map by {no_of_testers} Testers working in " \
                        "{no_of_releases} Releases".format(no_of_testers = no_of_testers,
                                                            no_of_releases=release_count,))
                plt.xticks(fontsize=7, rotation=31)
                plt.yticks(fontsize=7, rotation=25)
                plt.savefig(self.regression_time_heatmap, bbox_inches="tight")
                plt.close()
                # plt.show()
        except Exception as e:
            raise self.prod_exception("NO DUMP IN progress for time heatmap")

    ######################
    ##DB Related Operation
    ######################
    
    def close_finished_release(self):
        pass
