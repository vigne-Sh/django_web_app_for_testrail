"""
This module maintains the authentication config parser
"""
import os,sys
from configparser import ConfigParser

from .testrail import *
from jira.client import JIRA
sys.path.insert(0, os.getcwd())
from raptr.post_man.mail import MailClient


class AuthParser(MailClient):

    def __init__(self):
        super().__init__()
        self.config=ConfigParser()
        self.config_file="login_auth.ini"
        self.testrail="testrail"
        self.jira="jira"
        self.config.read(self.config_file)

        """
        Testrail Client
        """
        self.client=APIClient(self.config[self.testrail]["testrail_server_url"])
        self.client.user=self.config[self.testrail]["user_email"]
        self.client.password=self.config[self.testrail]["user_api_key"]

        """
        Jira Client
        """
        self.jira_id=self.config[self.jira]["user_id"]
        self.jira_pass=self.config[self.jira]["user_pass"]
        self.jira_options = {"server": self.config[self.jira]["jira_server"]}
        self.jira_client = JIRA(options=self.jira_options, basic_auth = (self.jira_id, self.jira_pass))
