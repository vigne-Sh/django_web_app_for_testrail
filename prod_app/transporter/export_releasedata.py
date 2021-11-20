"""
This module deals with exporting testrail milestones / runs / plans based on timeevents
"""
from datetime import datetime, date, timezone

from .testrail_api_client import TestrailAPIClient


class ExportReleaseData(TestrailAPIClient):

    def __init__(self):
        super().__init__()
        # self.PROJECT_IDS=[49,132,146,236] #-> removed awa/awv
        self.PROJECT_IDS=[132] #-> removed awa/awv
        self.user_choice={'p':'plans','r':'runs'}

    def _get_user_input(self):
        self.user_input = input("#*#*#*# select \np => plans\nr => runs\n#*#*#*#*\nEnter Your choice: \n")
        self.user_input = self.user_input.lower()
        if self.user_input not in self.user_choice.keys():
            self.log.error("wrong input please try again with input values \np=>plans\nr=>runs")
            raise SystemExit
        else:
            self.get_suite_id_choice = input("Enter SUITE ID \n y = yes \n n = no \n input=>")
            if self.get_suite_id_choice == 'y':
                self.get_suite_id_input = input("Enter Suite ID \n without space seperated by comma:")
                self.get_suite_id_input = self.get_suite_id_input.replace(" ", "")
            else:
                self.get_suite_id_input = 0
            self.log.info("User input =>%s",self.user_choice[self.user_input])
            start = input("#*#*#*#\nenter start date (yyyy-mm-dd): ")
            start_value  = start.split("-")
            start_timestamp = datetime(int(start_value[0]), int(start_value[1]), int(start_value[2]))
            start_timestamp = start_timestamp.replace(tzinfo= timezone.utc).timestamp()
            end = input("enter end date (yyyy-mm-dd) : ")
            end_value  = end.split("-")
            end_timestamp = datetime(int(end_value[0]), int(end_value[1]), int(end_value[2]))
            end_timestamp = end_timestamp.replace(tzinfo= timezone.utc).timestamp()
        return start_timestamp, end_timestamp, self.user_choice[self.user_input], \
                self.user_input, self.get_suite_id_input

    def _get_release_data(self):
        m = []
        runs_r_plans_list = []
        runs_plans_count = 0
        self.from_start_date, self.to_end_date, \
            self.user_selection, self.user_value, self.suite_id = self._get_user_input()
        self.log.info("Fetching => %s", self.user_selection)
        for project_id in self.PROJECT_IDS:
            offset = 0
            stop = False
            while stop == False:
                if self.user_selection == self.user_choice[self.user_value]:
                    release_data = self._fetch_plans(project_id=project_id, created_after =int(self.from_start_date),
                                    created_before=int(self.to_end_date), limit=250,offset=offset, suite_id=self.suite_id)
                elif self.user_selection == self.user_choice[self.user_selection]:
                    release_data = self._fetch_runs(project_id=project_id, created_after =int(self.from_start_date),
                                   created_before=int(self.to_end_date), limit=250,offset=offset, suite_id=self.suite_id)
                else:
                    self.log.error("Wrong INPUT, Please Try again")
                    raise SystemExit
                count = 0
                self.log.info("Release Data\n %s",release_data)
                self.log.info("\n~*~*~*~*~*~*~PROJECT ID => %s~*~*~*~*~*~*~\n", project_id)
                for data in release_data:
                    count += 1
                    release_date = date.fromtimestamp(data['created_on'])
                    if data['milestone_id'] is None and (data["passed_count"]+data["blocked_count"]+data["retest_count"]+data["blocked_count"]+data["failed_count"] + data['custom_status1_count']) > 0:
                        self.log.info("only %s => %s %s", self.user_selection, data['id'], release_date)
                        runs_r_plans_list.append(data['id'])
                        with open('{}.txt'.format(self.user_selection), 'w') as file:
                            for tc_data in runs_r_plans_list:
                                file.write("{}\n".format(tc_data))
                        runs_plans_count += 1
                    elif data['milestone_id'] is not None and (data["passed_count"]+data["blocked_count"]+data["retest_count"]+data["blocked_count"]+data["failed_count"] + data['custom_status1_count']) > 0:
                        self.log.info("milestone %s => %s", data['milestone_id'], release_date)
                        m.append(data['milestone_id'])

                self.log.info('%s id offset_limit=%s\n', project_id, count)
                if count >= 250:
                    offset += 250
                else:
                    stop = True
                    self.log.info("Fetching Release over.!")

        self.log.info('Milestones before compression %s',len(m))
        m1 = list(dict.fromkeys(m))
        with open('milestones_{}.txt'.format(self.user_value), 'w') as mil:
            for m_data in m1:
                mil.write("{}\n".format(m_data))
        rp = list(dict.fromkeys(runs_r_plans_list))
        self.log.info("Total No of Releases Exported => %s %s , unique Milestones =>%s",
                      len(rp),self.user_selection,len(m1))

#export time base data
# z = ExportReleaseData()
# z._get_release_data()