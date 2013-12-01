
from django.contrib.auth import (authenticate, login as auth_login,
                                               logout as auth_logout)
from django.contrib.auth.decorators import login_required
from django.contrib.messages import info, error
from django.core.urlresolvers import NoReverseMatch
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.utils.translation import ugettext_lazy as _
from django.template import RequestContext
from django.utils import simplejson

from mezzanine.utils.models import get_user_model
from mezzanine.accounts import get_profile_form
from mezzanine.accounts.forms import LoginForm, PasswordResetForm
from mezzanine.conf import settings
from mezzanine.utils.email import send_verification_mail, send_approve_mail
from mezzanine.utils.urls import login_redirect, get_login_redirect_url
from mezzanine.utils.views import render


User = get_user_model()


def login(request, template="accounts/account_login.html"):
    """
    Login form.
    """
    isAjax = False
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        authenticated_user = form.save()
        info(request, _("Successfully logged in"))
        auth_login(request, authenticated_user)
        if request.is_ajax():
            if  request.user.is_authenticated():
                next = get_login_redirect_url(request)
                return HttpResponse(simplejson.dumps(dict(url=next,
                                                          success=True)))
            else:
                return HttpResponse(simplejson.dumps(dict(success=False)))                
        else:
            return login_redirect(request)
    elif form.errors:
        return HttpResponse(simplejson.dumps(dict(errors=form.errors, success=False)))

    if request.is_ajax():
        template = "accounts/ajax_account_login.html"

    context = {"form": form, "title": _("Log in")}
    return render(request, template, context)


def logout(request):
    """
    Log the user out.
    """
    auth_logout(request)
    info(request, _("Successfully logged out"))
    return redirect(request.GET.get("next", "/"))


def signup(request, template="accounts/account_signup.html"):
    """
    Signup form.
    """
    profile_form = get_profile_form()
    form = profile_form(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        new_user = form.save()
        if not new_user.is_active:
            if settings.ACCOUNTS_APPROVAL_REQUIRED:
                send_approve_mail(request, new_user)
                info(request, _("Thanks for signing up! You'll receive "
                                "an email when your account is activated."))
            else:
                send_verification_mail(request, new_user, "signup_verify")
                info(request, _("A verification email has been sent with "
                                "a link for activating your account."))
            return redirect(request.GET.get("next", "/"))
        else:
            info(request, _("Successfully signed up"))
            auth_login(request, new_user)
            return login_redirect(request)
    context = {"form": form, "title": _("Sign up")}
    return render(request, template, context)


def signup_verify(request, uidb36=None, token=None):
    """
    View for the link in the verification email sent to a new user
    when they create an account and ``ACCOUNTS_VERIFICATION_REQUIRED``
    is set to ``True``. Activates the user and logs them in,
    redirecting to the URL they tried to access when signing up.
    """
    if settings.ACCOUNTS_APPROVAL_REQUIRED:
        raise Http404
    user = authenticate(uidb36=uidb36, token=token, is_active=False)
    if user is not None:
        user.is_active = True
        user.save()
        auth_login(request, user)
        info(request, _("Successfully signed up"))
        return login_redirect(request)
    else:
        error(request, _("The link you clicked is no longer valid."))
        return redirect("/")


@login_required
def profile_redirect(request):
    """
    Just gives the URL prefix for profiles an action - redirect
    to the logged in user's profile.
    """
    return redirect("profile", username=request.user.username)


def profile(request, username, template="accounts/account_profile.html"):
    """
    Display a profile.
    """
    lookup = {"username__iexact": username, "is_active": True}
    context = {"profile_user": get_object_or_404(User, **lookup)}
    return render(request, template, context)


@login_required
def account_redirect(request):
    """
    Just gives the URL prefix for accounts an action - redirect
    to the profile update form.
    """
    return redirect("profile_update")


@login_required
def profile_update(request, template="accounts/account_profile_update.html"):
    """
    Profile update form.
    """
    profile_form = get_profile_form()
    form = profile_form(request.POST or None, request.FILES or None,
                        instance=request.user)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        info(request, _("Profile updated"))
        try:
            return redirect("profile", username=user.username)
        except NoReverseMatch:
            return redirect("profile_update")
    context = {"form": form, "title": _("Update Profile")}
    return render(request, template, context)


def password_reset(request, template="accounts/account_password_reset.html"):
    form = PasswordResetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        send_verification_mail(request, user, "password_reset_verify")
        info(request, _("A verification email has been sent with "
                        "a link for resetting your password."))
    context = {"form": form, "title": _("Password Reset")}
    return render(request, template, context)


def password_reset_verify(request, uidb36=None, token=None):
    user = authenticate(uidb36=uidb36, token=token, is_active=True)
    if user is not None:
        auth_login(request, user)
        return redirect("profile_update")
    else:
        error(request, _("The link you clicked is no longer valid."))
        return redirect("/")
