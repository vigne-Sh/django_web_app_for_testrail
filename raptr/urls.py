from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.home, name = 'home'),
    path('login/', views.login_prod, name = 'login'),
    path('logout/', views.logout_prod, name = 'logout'),
    path('user_profile/', views.user_profile, name = 'user_profile'),
    path('generate_report/', views.generate_report, name = 'generate_report'),
    path('generate_report/<int:rnd_id>', views.display_report, name = 'display_report'),
    path('generate_bug_report/', views.generate_bug_report, name = 'generate_bug_report'),
    path('display_bug_report/release_id=<int:release_id>', views.display_bug_report, name = 'display_bug_report'),
    path('display_testrail_db/', views.display_testrail_database, name = 'display_testrail_db'),
    path('display_mailer_db/', views.display_mailer_database, name = 'display_mailer_db'),
    path('edit_mailer_db/team=<str:team_updating>', views.edit_mailer_db, name = 'edit_mailer_db'),
    path('update_mailer_db/team=<str:team_updating>', views.update_mailer_db, name = 'update_mailer_db'),
    path('display_db/', views.display_database, name = 'display_all'),
    path('display_db/add_release', views.add_release, name = 'add_db'),
    path('display_db/edit_release/<int:rl_id>', views.edit_release, name = 'edit_db'),
    path('display_db/update_releases/<int:rl_id>', views.update_releases, name = 'update_db'),
    path('delete_release/<int:dl_id>', views.delete_release, name = 'delete_db'),
    path('about_productivity/', views.about_productivity, name = 'about_productivity')
]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
