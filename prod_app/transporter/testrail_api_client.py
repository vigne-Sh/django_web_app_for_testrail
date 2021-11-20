"""
this module deals with all the api activites from testrail
"""

from .auth_parser import AuthParser

class TestrailAPIClient(AuthParser):

    def __init__(self):
        super().__init__()
        self.project_dict={
                            49:"ELEVEN",
                            132:"SMARTTV",
                            146:"WHISKEY",
                            236:"MARTY",
                            121:"AWV / AWA"
                          }

    def _get_milestone_name(self, milestone_id):
        """
        get milestone name
        
        :param milestone_id: release milestone id 
        :return: milestone name
        """
        try:
            fetch_mid = self.client.send_get('get_milestone/{}'.format(milestone_id))
            name = fetch_mid['name']
            return name
        except:
            return ''

    def _get_plan_name(self, plan_id):
        """
        get plan name
        
        :param plan_id: release plan id 
        :return: plan name
        """
        try:
            fetch_pid = self.client.send_get('get_plan/{}'.format(plan_id))
            name = fetch_pid['name']
            return name
        except:
            return ''

    def _get_run_name(self, run_id):
        """
        get run name
        
        :param run_id: release run id 
        :return: run name
        """
        try:
            fetch_rid = self.client.send_get('get_run/{}'.format(run_id))
            name = fetch_rid['name']
            return name
        except:
            return ''

    def _get_user_name(self, user_id):
        """
        get testrail user name
        
        :param user_id: amazon user id 
        :return: testrail name
        """
        try:
            user = self.client.send_get('get_user_by_email&email={}@amazon.com'.format(user_id))
            return user['name']
        except:
            return ''

    def verify_if_valid_release(self, rl_id, rl_type):
        """
        verify if release is valid
        
        :param release_id: release id 
        :return: bool, if valid release
        """
        release_name=""
        if rl_type=="milestone":
            release_name=self._get_milestone_name(rl_id)
        elif rl_type=="plan":
            release_name=self._get_plan_name(rl_id)
        elif rl_type=="run":
            release_name=self._get_run_name(rl_id)
        return bool(release_name)

    def _fetch_plans(self, project_id, created_after, created_before, limit, offset, suite_id=None):
        if not suite_id:
            suite_id = ''
        get_plan_data = self.client.send_get("get_plans/{}&created_after={}&" \
                                             "created_before={}&limit={}&offset={}&suite_id={}" \
                                             .format(project_id,created_after,created_before,
                                                      limit,offset, suite_id))
        return get_plan_data

    def _fetch_runs(self, project_id, created_after, created_before, limit, offset, suite_id=None):
        if not suite_id:
            suite_id = ''
        get_run_data = self.client.send_get("get_runs/{}&created_after={}&" \
                                             "created_before={}&limit={}&offset={}&suite_id={}" \
                                             .format(project_id,created_after,created_before,
                                                      limit,offset, suite_id))
        return get_run_data

    def _get_project_id(self, rtype, rid):
        return self.client.send_get("get_{}/{}".format(rtype, rid))['project_id']

    def _get_release_and_project_name_(self, rtype, rid):
        try:
            relesae_data = self.client.send_get("get_{}/{}".format(rtype, rid))
            return relesae_data['name'], relesae_data['project_id']
        except:
            self.log.error("Exception hit [%s]", e)
            return '', ''
