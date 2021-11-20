from sqlite3.dbapi2 import Cursor
import pandas as pd
import sqlite3
import random
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, HttpResponse
from django.contrib import messages
from django.views.generic import TemplateView
from django.views.decorators.csrf import  csrf_exempt, csrf_protect

from .models import *
from .remove_duplicates import check_distinct
from prod_wsgi.settings import ADMIN_ROLE, TESTRAIL_DB_ACCESS, SESSION_COOKIE_AGE
from .decorator import login_required
from .forms import edit_releaseform, edit_mailerinfo

from .transporter.dump_scraper_client import DumpScraper
from .transporter.testrail_api_client import TestrailAPIClient
from .report_constructor.regression_prod_report import DailyProdReportWebApp
from .report_constructor.bug_validation_report import BugValidationReport
from .post_man.ldap_client import *


insant_report=DailyProdReportWebApp()
bug_report_client=BugValidationReport()
export_dump=DumpScraper()
report_type="web_app_prod_report"
testrail_api=TestrailAPIClient()

class AuthView(TemplateView):
    """Launch the login page"""
    template_name='login_prod.html'

def verify_if_already_added(rl_id):
    sql_connection=sqlite3.connect('db.sqlite3')
    cursor=sql_connection.cursor()
    df=pd.read_sql_query('select * from raptr_update_release where releaseid={}'.format(rl_id), sql_connection)
    if len(df):
        return len(df)
    else:
        return 0

def verify_if_valid_edit(rl_id):
    sql_connection=sqlite3.connect('db.sqlite3')
    cursor=sql_connection.cursor()
    df=pd.read_sql_query('select * from raptr_update_release where releaseid={}'.format(rl_id), sql_connection)
    if len(df):
        return int(df["releaseid"]), str(df["releasename"])
    else:
        return 0

def return_stats_count():
    sql_connection=sqlite3.connect('db.sqlite3')
    df=pd.read_sql_query('select sum(report_count) as total from raptr_prod_app_stats', sql_connection)
    df=df[df.total.notnull()]
    if not len(df["total"]):
        return 0
    else:
        return sum(df["total"])

def return_stats_table():
    sql_connection=sqlite3.connect('db.sqlite3')
    cursor=sql_connection.cursor()
    cursor.execute("select user_id, sum(report_count) from raptr_prod_app_stats group by user_id")
    table=cursor.fetchall()
    return table

# Define Views below

@login_required
@csrf_exempt
def home(request):
    try:
        if "user_name" in request.session:
            a = request.session.get_expiry_age()
            user_name={"user_name" : request.session["user_name"], "user_id" : request.session["user_id"]}
            return render(request, 'home_page.html', user_name)
    except Exception as e:
        return redirect('login')

@csrf_protect
def login_prod(request):
    """
    login portal for web app
    """
    if "user_id" not in request.session:
        if request.POST:
            get_login_data=request.POST
            user_id=get_login_data.get('user_id')
            password=get_login_data.get('user_pass')
            try:
                user=authenticate_user(user_id, password)
                if user: 
                    employee_name ,employee_role, employee_level , employee_manager, employee_jobservice = get_employee_profile(user_id)
                    user_entry=user_db()
                    user_entry.user_id=user_id
                    user_entry.user_name=employee_name
                    request.session["user_id"]=user_id
                    request.session["user_name"]=employee_name
                    request.session['user_key'] = password
                    request.session['user_role'] = employee_role
                    request.session['user_level'] = employee_level
                    request.session['user_manager'] = employee_manager
                    request.session['user_jobservice'] = employee_jobservice
                    # request.session.set_expiry(SESSION_COOKIE_AGE) # => to get session age
                    user_entry.user_mgr=employee_manager
                    user_entry.user_pass=password
                    user_entry.save()
                    messages.success(request, 'Login Successfull')
                    return redirect('/')
                elif not user:
                    messages.error(request, 'incorrect credentials please try again')
                    return redirect('login')
            except Exception as e:
                print(e)
                return render(request, 'login_prod.html')
        else:
            return render(request, 'login_prod.html')
    else:
        return redirect('home')

@login_required
@csrf_protect
def generate_report(request):
    milestone_ids_list=[]
    plan_ids_list=[]
    run_ids_list=[]
    random_val=random.randint(1*11111, 7*22222)
    user_name={"user_name" : request.session["user_name"], "user_id" : request.session["user_id"] }
    if request.POST:
        release_form=request.POST
        mid=release_form.get('milestone')
        pid=release_form.get('plan')
        rid=release_form.get('run')
        if mid:
            milestone_ids_list=mid.split(',')
            milestone_ids_list=[int(val) for val in milestone_ids_list]
        if pid:
            plan_ids_list=pid.split(',')
            plan_ids_list=[int(val) for val in plan_ids_list]
        if rid:
            run_ids_list=rid.split(',')
            run_ids_list=[int(val) for val in run_ids_list]
        export_dict={
                "milestones" : milestone_ids_list,
                "plans" : plan_ids_list,
                "runs" : run_ids_list,
            }
        try:
            if len(milestone_ids_list):
                for m in milestone_ids_list:
                    export_dump.export_csv_with_export_type(rid=m, export_type= 'milestone', report_type= report_type)
            if len(plan_ids_list):
                for p in plan_ids_list:
                    export_dump.export_csv_with_export_type(rid=p, export_type= 'plan', report_type= report_type)
            if len(run_ids_list):
                for r in run_ids_list:
                    export_dump.export_csv_with_export_type(rid= r, export_type= 'run', report_type= report_type)
            if len(export_dict):
                rl_id={'random_int': random_val}
                request.session['release_list']=export_dict
                return redirect('display_report' , rnd_id=rl_id["random_int"])
        except Exception as e:
            if not len(export_dict):
                return redirect('generate_report')
    return render(request, 'generate_report.html', user_name)

@login_required
@csrf_protect
def generate_bug_report(request):
    bug_validation_data = {"user_name" : request.session["user_name"], "user_id" : request.session["user_id"]}
    alias = "@amazon.com"
    send_to_user = request.session["user_id"] + alias
    to_user = [send_to_user]
    cc_user = [send_to_user]
    if request.POST:
        bug_form = request.POST
        report_id = bug_form.get("team_name")
        bug_report = bug_report_client.generate_report_and_mail_it(to_addr=to_user, cc_addr=cc_user, using_tool=True)
        request.session['bug_content'] = bug_report
        return redirect('display_bug_report', release_id=report_id)
    return render(request, 'generate_bug_validation_report.html', bug_validation_data)

@login_required
@csrf_exempt
def display_bug_report(request, release_id):
    bug_report_data = {"user_name" : request.session["user_name"],
                       "user_id" : request.session["user_id"], 
                       "bug_report": request.session['bug_content']}
    return render(request, "display_bug_report.html",  bug_report_data)

@login_required
@csrf_exempt
def user_profile(request):
    try:
        user_data = {
                    'user_id':request.session['user_id'],
                    'username':request.session['user_name'],
                    'user_key':request.session['user_key'],
                    'user_role':request.session['user_role'],
                    'user_level':request.session['user_level'],
                    'user_manager':request.session['user_manager'],
                    'user_jobservice':request.session['user_jobservice'], 
                    }
        return render(request, 'user_profile.html', user_data)
    except Exception as e:
        return HttpResponse("Failed {error}".format(error = e))
        # return redirect('home')


@login_required
def display_report(request, rnd_id):
    try:
        prod_export_report_table=insant_report.get_instant_prod_report(request.session['release_list'])
        if prod_export_report_table:
            prod_report={'prod_report': """
                                            {}
                                        """.format(prod_export_report_table[0]), 
                        'release_report' : """
                                                {}
                                                """.format(prod_export_report_table[1]),
                        "user_name" : request.session["user_name"], 
                        "user_id" : request.session["user_id"]
                            }
            prod_db=prod_app_stats()
            prod_db.user_id=request.session["user_id"]
            prod_db.report_count=1
            prod_db.save()
            return render(request, 'display_report.html', prod_report)
    except Exception as e:
        messages.error(request, "Release ID In-correct..! Please Check Your release id and try again")
        return redirect('generate_report')

@login_required
@csrf_exempt
def display_database(request):
    try:
        db_objects=update_release.objects.all()
        display_release={"display_release" : db_objects, "user_name" : request.session["user_name"], "user_id" : request.session["user_id"]}
        return render(request, 'display_database.html', display_release)  
    except:
        return redirect('login')
    
@login_required
@csrf_exempt
def display_testrail_database(request):
    try:
        if request.session["user_id"] in TESTRAIL_DB_ACCESS:
            check_distinct()
            testrail_database=testrail_db.objects.all()
            messages.success(request, 'Testrail execution Count')
            testrail_db_pointer={"testrail_db_pointer" : testrail_database, "user_name" : request.session["user_name"], "user_id" : request.session["user_id"]}
            return render(request, 'display_testrail_database.html', testrail_db_pointer)
        else:
            messages.error(request, 'No Permission to View')
            return redirect('home')
    except Exception as e:
        return redirect('login')

@login_required
@csrf_exempt
def display_mailer_database(request):
    try:
        mailer_objects=mailer_db.objects.all()
        if request.session["user_id"]:
            mailer_db_data={"mailer_db_data": mailer_objects ,"user_name" : request.session["user_name"], "user_id" : request.session["user_id"]}
            return render(request, 'display_mailer_database.html', mailer_db_data)
        else:
            messages.error(request, 'No Permission to View')
            return redirect('home')
    except Exception as e:
        return redirect('login')

@login_required
@csrf_protect
def edit_mailer_db(request, team_updating):
    try:
        if request.session["user_id"] in ADMIN_ROLE:
            mailer_objects=mailer_db.objects.get(team_name=team_updating)
            edit_mailers={"edit_mailers": mailer_objects, "user_name" : request.session["user_name"], "user_id" : request.session["user_id"]}
            return render(request, 'edit_mailers.html', edit_mailers)
        else:
            messages.error(request, 'Please Contact Admin to Edit')
            return redirect('display_mailer_db')
    except:
        return redirect('login')

@login_required
@csrf_protect
def update_mailer_db(request, team_updating):
    try:
        mailer_data=mailer_db.objects.get(team_name=team_updating)
        update_mailers={"update_mailers": mailer_data, "user_name" : request.session["user_name"], "user_id" : request.session["user_id"]}
        update_mail_info=edit_mailerinfo(request.POST, instance=mailer_data)
        if update_mail_info.is_valid():
            update_mail_info.save()
            return redirect('display_mailer_db')
        else:
            messages.error(request, "Not a Valid Info, check with admin for exact format")
            return redirect('home')
    except Exception as e:
        return redirect('login')
    
@login_required
@csrf_protect
def edit_mail_release(request, rl_id):
    try:
        release_database=update_release.objects.get(releaseid=rl_id)
        edit_release={"edit_release" : release_database, "user_name" : request.session["user_name"], "user_id" : request.session["user_id"]}
        return render(request, 'edit_release.html', edit_release)
    except:
        return redirect('display_all')

@login_required
@csrf_protect
def update_mail_releases(request, rl_id):
    try:
        print("hititng here")
        release_db=update_release.objects.get(releaseid=rl_id)
        update_releases={"edit_release" : release_db, "user_name" : request.session["user_name"] , "user_id" : request.session["user_id"]}
        edit_form=edit_releaseform(request.POST, instance=release_db)
        if edit_form.is_valid():
                if testrail_api.verify_if_valid_release(edit_form.instance.releaseid, edit_form.instance.releasetype):
                    messages.success(request, "Successfully Update the Release")
                    edit_form.save()
                    return redirect('display_all')
                else:
                    messages.error(request, "Not a Valid Release, Please Update with correct Release data")
                    return redirect('display_all')
    except Exception as e:
        return redirect('login')

@login_required
@csrf_protect
def add_release(request):
    try:
        user_name={"user_name" : request.session["user_name"] , "user_id" : request.session["user_id"]}
        date=datetime.today().strftime("%b-%d-%Y")
        if request.POST:
            request_data=request.POST
            team_name=request_data.get('team_name')
            release_name=request_data.get('release_name')
            rid=request_data.get('rid')
            release_type=request_data.get('release_type')
            release_status=request_data.get('release_status')
            if verify_if_already_added(rid):
                messages.warning(request, 'Release ID exits,  please check properly')
                return redirect('display_all')
            if testrail_api.verify_if_valid_release(rid, release_type):
                release_opr=update_release()
                release_opr.teamname=team_name
                release_opr.releaseid =rid
                release_opr.releasetype=release_type
                release_opr.releasename=release_name
                release_opr.releasestatus=release_status
                release_opr.releasedate=str(date)
                release_opr.addedby=request.session["user_id"]
                release_opr.save()
                messages.success(request, 'Release Added Successfully')
                return redirect('display_all')
            else: 
                messages.warning(request, 'Incorrect Release ID or Release Type, Please add properly')
                return redirect('display_all')
        return render(request, 'add_release.html', user_name) 
    except Exception as e:
        return redirect('login')

@login_required
@csrf_protect
def edit_release(request, rl_id):
    try:
        release_database=update_release.objects.get(releaseid=rl_id)
        edit_release={"edit_release" : release_database, "user_name" : request.session["user_name"], "user_id" : request.session["user_id"]}
        return render(request, 'edit_release.html', edit_release)
    except:
        return redirect('display_all')

@login_required
@csrf_protect
def update_releases(request, rl_id):
    try:
        release_db=update_release.objects.get(releaseid=rl_id)
        update_releases={"edit_release" : release_db, "user_name" : request.session["user_name"] , "user_id" : request.session["user_id"]}
        edit_form=edit_releaseform(request.POST, instance=release_db)
        if edit_form.is_valid():
                if testrail_api.verify_if_valid_release(edit_form.instance.releaseid, edit_form.instance.releasetype):
                    messages.success(request, "Successfully Update the Release")
                    edit_form.save()
                    return redirect('display_all')
                else:
                    messages.error(request, "Not a Valid Release, Please Update with correct Release data")
                    return redirect('display_all')
    except Exception as e:
        return redirect('login')

@login_required
def delete_release(request, dl_id):
    try:
        release_db=update_release.objects.get(releaseid=dl_id)
        if request.session["user_id"] in ADMIN_ROLE:
            release_db.delete()
            messages.success(request, 'Release Deleted from Database Successfully')
            return redirect('display_all')
        else:
            messages.error(request, 'No permission to modify')
            return redirect('display_all')
    except:
        return redirect('login')

@login_required
@csrf_exempt
def about_productivity(request):
    try:
        about_db=return_stats_table
        user_name={"user_name" : request.session["user_name"] , "user_id" : request.session["user_id"], "total_stats": return_stats_count(), "stats_info": about_db}
        return render(request, 'about_productivity.html', user_name)
    except Exception as e:
        return redirect('login')

def logout_prod(request):
    """Session logout"""
    try:
        request.session.clear()
        # return render(request, 'logout_prod.html')
        return redirect('login')
    except:
        pass
