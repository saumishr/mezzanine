
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.messages import error
from django.core.urlresolvers import reverse
from django.db.models import get_model, ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.simplejson import dumps
from django.utils.translation import ugettext_lazy as _
from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.contenttypes.models import ContentType

from mezzanine.conf import settings
from mezzanine.generic.forms import ThreadedCommentForm, RatingForm, ReviewForm
from mezzanine.generic.models import Keyword
from mezzanine.utils.cache import add_cache_bypass
from mezzanine.utils.views import render, set_cookie, is_spam
from mezzanine.blog.models import BlogPost

from actstream import action

@staff_member_required
def admin_keywords_submit(request):
    """
    Adds any new given keywords from the custom keywords field in the
    admin, and returns their IDs for use when saving a model with a
    keywords field.
    """
    keyword_ids, titles = [], []
    for title in request.POST.get("text_keywords", "").split(","):
        title = "".join([c for c in title if c.isalnum() or c in "- "]).strip()
        if title:
            try:
                keyword = Keyword.objects.get(title__iexact=title)
            except Keyword.DoesNotExist:
                keyword = Keyword.objects.create(title=title)
            keyword_id = str(keyword.id)
            if keyword_id not in keyword_ids:
                keyword_ids.append(keyword_id)
                titles.append(title)
    return HttpResponse("%s|%s" % (",".join(keyword_ids), ", ".join(titles)))


def initial_validation(request, prefix):
    """
    Returns the related model instance and post data to use in the
    comment/rating views below.

    Both comments and ratings have a ``prefix_ACCOUNT_REQUIRED``
    setting. If this is ``True`` and the user is unauthenticated, we
    store their post data in their session, and redirect to login with
    the view's url (also defined by the prefix arg) as the ``next``
    param. We can then check the session data once they log in,
    and complete the action authenticated.

    On successful post, we pass the related object and post data back,
    which may have come from the session, for each of the comments and
    ratings view functions to deal with as needed.
    """
    post_data = request.POST
    settings.use_editable()
    login_required_setting_name = prefix.upper() + "S_ACCOUNT_REQUIRED"
    posted_session_key = "unauthenticated_" + prefix
    redirect_url = ""
    if getattr(settings, login_required_setting_name, False):
        if not request.user.is_authenticated():
            request.session[posted_session_key] = request.POST
            error(request, _("You must logged in. Please log in or "
                             "sign up to complete this action."))
            redirect_url = "%s?next=%s" % (settings.LOGIN_URL, reverse(prefix))
        elif posted_session_key in request.session:
            post_data = request.session.pop(posted_session_key)
    if not redirect_url:
        try:
            model = get_model(*post_data.get("content_type", "").split(".", 1))
            if model:
                obj = model.objects.get(id=post_data.get("object_pk", None))
        except (TypeError, ObjectDoesNotExist):
            redirect_url = "/"
    if redirect_url:
        if request.is_ajax():
            return HttpResponse(dumps({"location": redirect_url}))
        else:
            return redirect(redirect_url)
    return obj, post_data


def comment(request, template="generic/comments.html"):
    """
    Handle a ``ReviewForm`` submission and redirect back to its
    related object.
    """
    response = initial_validation(request, "comment")
    if isinstance(response, HttpResponse):
        return response
    obj, post_data = response
    form = ReviewForm(request, obj, post_data)
    if form.is_valid():
        url = obj.get_absolute_url()
        if is_spam(request, form, url):
            return redirect(url)
        comment = form.save(request)
        response = redirect(add_cache_bypass(comment.get_absolute_url()))
        # Store commenter's details in a cookie for 90 days.
        for field in ReviewForm.cookie_fields:
            cookie_name = ReviewForm.cookie_prefix + field
            cookie_value = post_data.get(field, "")
            set_cookie(response, cookie_name, cookie_value)
        """
            Send activity feed to those who follow this vendor page.
        """
        action.send(obj, verb=u'has got a new review from', action_object=comment, target=request.user)
        return response
    elif request.is_ajax() and form.errors:
        return HttpResponse(dumps({"errors": form.errors}))
    # Show errors with stand-alone comment form.
    context = {"obj": obj, "posted_comment_form": form}
    if obj.ratingParameters :
        ratingParameters = obj.ratingParameters.split(',')
        for ratingParameter in ratingParameters :
            if post_data.get(ratingParameter + "_value") :
                context[ratingParameter + "_value"] = post_data.get(ratingParameter + "_value")
    response = render(request, template, context)
    return response


from django.template import RequestContext
def comment_on_review(request, template="generic/comments.html"):
    """
    Handle a ``ThreadedCommentForm`` submission and redirect back to its
    related object.
    """

    response = initial_validation(request, "comment")
    if isinstance(response, HttpResponse):
        return response
    obj, post_data = response

    form = ThreadedCommentForm(request, obj, post_data)
    if form.is_valid():
        url = obj.get_absolute_url()
        if is_spam(request, form, url):
            return redirect(url)  
        comment = form.save(request)
        response = redirect(add_cache_bypass(comment.get_absolute_url()))

        return response
    elif request.is_ajax() and form.errors:
        return HttpResponse(dumps({"errors": form.errors}))

    # Show errors with stand-alone comment form.
    context = {"obj": obj, "posted_comment_form": form}
    response = render(request, template, context)
    return response

def fetch_comments_on_obj(request, content_type_id, object_id):
    ctype = get_object_or_404(ContentType, pk=content_type_id)
    parent = get_object_or_404(ctype.model_class(), pk=object_id)
    comments = []
    if request.user.is_staff:
        comments_queryset = parent.comments.all()
    else:
        comments_queryset = parent.comments.visible()

    for comment in comments_queryset.select_related("user"):
        comments.append(comment) 

    return render_to_response('generic/includes/subcomment.html', {
       'comments_for_thread': comments, 
    }, context_instance=RequestContext(request))

def rating(request):
    """
    Handle a ``RatingForm`` submission and redirect back to its
    related object.
    """
    response = initial_validation(request, "rating")
    if isinstance(response, HttpResponse):
        return response
    obj, post_data = response
    url = add_cache_bypass(obj.get_absolute_url().split("#")[0])
    response = redirect(url + "#rating-%s" % obj.id)
    rating_form = RatingForm(request, obj, post_data)
    if rating_form.is_valid():
        rating_form.save()
        if request.is_ajax():
            # Reload the object and return the rating fields as json.
            obj = obj.__class__.objects.get(id=obj.id)
            rating_name = obj.get_ratingfield_name()
            json = {}
            for f in ("average", "count", "sum"):
                json["rating_" + f] = getattr(obj, "%s_%s" % (rating_name, f))
            response = HttpResponse(dumps(json))
        ratings = ",".join(rating_form.previous + [rating_form.current])
        set_cookie(response, "mezzanine-rating", ratings)
    return response


def commentProfile(request, username):
    """
    Get the profile of the comment owner
    """
    return HttpResponseRedirect(
              reverse("mezzanine.accounts.views.profile", 
                      args=[username]))

def comment_thread_most_liked_view(request, obj, template="generic/includes/comments_most_liked.html"):
    """
    Return a list of child comments for the given parent, storing all
    comments in a dict in the context when first called, using parents
    as keys for retrieval on subsequent recursive calls from the
    comments template.
    """
    from mezzanine.generic.forms import ThreadedCommentForm

    parent = BlogPost.objects.get(id=obj)
    context = RequestContext(request)
    form = ReviewForm(request, parent)
    try:
        context["posted_comment_form"]
    except KeyError:
        context["posted_comment_form"] = form
    context["unposted_comment_form"] = form
    context["comment_url"] = reverse("comment")
    context["object_for_comments"] = parent
    return render(request, template, context)
 
def comment_thread_most_recent_view(request, obj, template="generic/includes/comments_most_recent.html"):
    """
    Return a list of child comments for the given parent, storing all
    comments in a dict in the context when first called, using parents
    as keys for retrieval on subsequent recursive calls from the
    comments template.
    """
    from mezzanine.generic.forms import ThreadedCommentForm

    parent = BlogPost.objects.get(id=obj)
    context = RequestContext(request)
    form = ReviewForm(request, parent)
    try:
        context["posted_comment_form"]
    except KeyError:
        context["posted_comment_form"] = form
    context["unposted_comment_form"] = form
    context["comment_url"] = reverse("comment")
    context["object_for_comments"] = parent
    return render(request, template, context)

 
def comment_thread_default_view(request, obj, template="generic/includes/comments.html"):
    """
    Return a list of child comments for the given parent, storing all
    comments in a dict in the context when first called, using parents
    as keys for retrieval on subsequent recursive calls from the
    comments template.
    """
    from mezzanine.generic.forms import ReviewForm

    parent = BlogPost.objects.get(id=obj)
    context = RequestContext(request)
    form = ReviewForm(request, parent)
    try:
        context["posted_comment_form"]
    except KeyError:
        context["posted_comment_form"] = form
    context["unposted_comment_form"] = form
    context["comment_url"] = reverse("comment")
    context["object_for_comments"] = parent
    return render(request, template, context)

def comment_thread_social_view(request, obj, template="generic/includes/comments_social.html"):
    """
    Return a list of child comments for the given parent, storing all
    comments in a dict in the context when first called, using parents
    as keys for retrieval on subsequent recursive calls from the
    comments template.
    """
    from mezzanine.generic.forms import ThreadedCommentForm

    parent = BlogPost.objects.get(id=obj)
    context = RequestContext(request)
    form = ReviewForm(request, parent)
    try:
        context["posted_comment_form"]
    except KeyError:
        context["posted_comment_form"] = form
    context["unposted_comment_form"] = form
    context["comment_url"] = reverse("comment")
    context["object_for_comments"] = parent
    return render(request, template, context)

def comment_thread_social_view_level2(request, obj, template="generic/includes/comments_social_level2.html"):
    """
    Return a list of child comments for the given parent, storing all
    comments in a dict in the context when first called, using parents
    as keys for retrieval on subsequent recursive calls from the
    comments template.
    """
    from mezzanine.generic.forms import ThreadedCommentForm

    parent = BlogPost.objects.get(id=obj)
    context = RequestContext(request)
    form = ReviewForm(request, parent)
    try:
        context["posted_comment_form"]
    except KeyError:
        context["posted_comment_form"] = form
    context["unposted_comment_form"] = form
    context["comment_url"] = reverse("comment")
    context["object_for_comments"] = parent
    return render(request, template, context)