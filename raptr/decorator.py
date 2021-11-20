from django.http import HttpResponseRedirect

def login_required(f):
    def wrap(request, *args, **kwargs):
        # this check the session if userid key exist, if not it will redirect to login page
        if not request.session.has_key('user_name'):
            return HttpResponseRedirect("/login/")
        return f(request, *args, **kwargs)
    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__
    return wrap