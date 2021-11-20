from django.db import models

class user_db(models.Model):
    user_id = models.CharField(max_length=300, default='user_id')
    user_name = models.CharField(max_length=700, default='user_name')
    user_mgr = models.CharField(max_length=700, default='user_manager')
    user_pass = models.CharField(max_length=300, default='user_pass')
    date = models.DateTimeField(auto_now_add=True)
class mailer_db(models.Model):
    team_name = models.CharField(max_length=300, default='team_name',blank=True)
    mailing_list = models.CharField(max_length=1000, default='email_alias', blank=True)
    team_mgr = models.CharField(max_length=700, default='user_manager', blank=True)
    report_timer = models.CharField(max_length=300, default='user_pass')
    date = models.DateTimeField(auto_now_add=True, null=True)

class prod_app_stats(models.Model):
    user_id = models.CharField(max_length=300, default='')
    report_count = models.IntegerField(default='')
    time = models.DateField(auto_now_add=True)

class update_release(models.Model):
    teamname = models.CharField(max_length=300, default='release name')
    releasename = models.CharField(max_length=300)
    releaseid = models.IntegerField()
    releasetype = models.CharField(max_length=300, default='release_type')
    releasestatus = models.CharField(max_length=300, default='release_status')
    releasedate = models.CharField(max_length=500, default='release_date', blank=True, null=True)
    addedby = models.CharField(max_length=500, default='release added by')

class testrail_db(models.Model):
    testrail_name = models.CharField(max_length=500, default='testrail_name')
    Date  = models.CharField(max_length=500, default='01/01/2021')
    total = models.IntegerField(default='70')
    manager = models.CharField(max_length=300, default="andy")
    user_id = models.CharField(max_length=300, default='amazon_user')
    ldap_name = models.CharField(max_length=700, default='ldap_user')