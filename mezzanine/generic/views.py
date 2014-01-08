from django import forms
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.messages import error
from django.core.urlresolvers import reverse
from django.db.models import get_model, ObjectDoesNotExist
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.utils import simplejson
from django.utils.simplejson import dumps
from django.utils.translation import ugettext_lazy as _
from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.template.loader import render_to_string
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from mezzanine.conf import settings
from mezzanine.generic.forms import ThreadedCommentForm, RatingForm, ReviewForm
from mezzanine.generic.models import Keyword, Review, RequiredReviewRating, OptionalReviewRating
from mezzanine.utils.cache import add_cache_bypass
from mezzanine.utils.views import render, set_cookie, is_spam
from mezzanine.blog.models import BlogPost

from actstream import action
import json

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
            if not request.POST:
            	request.POST = post_data
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

@login_required
def comment(request, template="generic/comments.html"):
    """
    Handle a ``ReviewForm`` submission and redirect back to its
    related object.
    """
    response = initial_validation(request, "comment")
    if isinstance(response, HttpResponse):
        return response
    obj, post_data = response
    form = ReviewForm(request, obj, request.POST )
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
        if request.user.is_authenticated():
            action.send(obj, verb=settings.GOT_REVIEW_VERB, target=comment )
        return response
    elif request.is_ajax() and form.errors:
        return HttpResponse(dumps({"errors": form.errors}))
    # Show errors with stand-alone comment form.
    context = {"obj": obj, "posted_comment_form": form}
    response = render(request, template, context)
    return response

@login_required
def write_review(request, content_type_id, object_id, template="generic/includes/write_review.html"):
	ctype = get_object_or_404(ContentType, pk=content_type_id)
	parent = get_object_or_404(ctype.model_class(), pk=object_id)
	
	if request.method == 'POST':
		response = initial_validation(request, "write_review")
		if isinstance(response, HttpResponse):
		    return response
		obj, post_data = response

		form = ReviewForm(request, obj, request.POST)
		if form.is_valid():
			url = obj.get_absolute_url()
			if is_spam(request, form, url):
				return redirect(url)  
			comment = form.save(request)

			"""
				Send activity feed to those who follow this vendor page.
			"""
			if request.user.is_authenticated():
				action.send(obj, verb=settings.GOT_REVIEW_VERB, target=comment )

			if request.is_ajax():
				html = render_to_string('generic/includes/comment_ajax.html', { 'comment': comment, 'request':request }) 
				res = {'html': html,
					   'success':True}
				response = HttpResponse( simplejson.dumps(res), 'application/json' )
				# Store commenter's details in a cookie for 90 days.
				for field in ReviewForm.cookie_fields:
					cookie_name = ReviewForm.cookie_prefix + field
					cookie_value = post_data.get(field, "")
					set_cookie(response, cookie_name, cookie_value)	
								
				return response
			else:
				response = redirect(add_cache_bypass(comment.get_absolute_url()))
				return response

		elif request.is_ajax() and form.errors:
			return HttpResponse( simplejson.dumps({"errors": form.errors,
										"success":False}), 'application/json')		
	else:
		form = ReviewForm(request, parent)
		form.fields['overall_value'].widget 	= forms.HiddenInput()
		form.fields['price_value'].widget 		= forms.HiddenInput()
		form.fields['variety_value'].widget 	= forms.HiddenInput()
		form.fields['quality_value'].widget 	= forms.HiddenInput()
		form.fields['service_value'].widget 	= forms.HiddenInput()
		form.fields['exchange_value'].widget 	= forms.HiddenInput()

		context = {"new_review":True,  "obj": parent, "posted_comment_form": form, "action_url": reverse("write_review", kwargs={
																												'content_type_id':content_type_id,
																												'object_id':object_id
																											})}
		response = render(request, template, context)
		return response



@login_required
def comment_on_review(request, template="generic/comments.html"):
    """
    Handle a ``ThreadedCommentForm`` submission and redirect back to its
    related object.
    """

    response = initial_validation(request, "comment_on_review")
    if isinstance(response, HttpResponse):
        return response
    obj, post_data = response

    form = ThreadedCommentForm(request, obj, request.POST)
    if form.is_valid():
        url = obj.get_absolute_url()
        if is_spam(request, form, url):
            return redirect(url)  
        comment = form.save(request)
        if request.is_ajax():
            #comment = form.save(request)
            comments = [comment]

            html = render_to_string('generic/includes/subcomment.html', { 'comments_for_thread': comments }) 
            res = {'html': html}
            return HttpResponse( simplejson.dumps(res), 'application/json' )
        else:
            response = redirect(add_cache_bypass(comment.get_absolute_url()))
            return response

    elif request.is_ajax() and form.errors:
        return HttpResponse(dumps({"errors": form.errors}))

    # Show errors with stand-alone comment form.
    if not request.is_ajax():
        context = {"obj": obj, "posted_comment_form": form}
        response = render(request, template, context)
        return response

def fetch_commenters_on_obj(request, content_type_id, object_id):
    ctype = get_object_or_404(ContentType, pk=content_type_id)
    parent = get_object_or_404(ctype.model_class(), pk=object_id)

    if request.user.is_staff:
        comments_queryset = parent.comments.all()
    else:
        comments_queryset = parent.comments.visible()

    commenter_ids =  comments_queryset.select_related("user").values_list('user', flat=True)
    commenters = User.objects.all().filter(id__in=set(commenter_ids))
    return render_to_response('generic/includes/commenters.html', {
       'commenters': commenters, 
    }, context_instance=RequestContext(request))

def fetch_range_commenters_on_obj(request, content_type_id, object_id, sIndex=0, lIndex=0):
    ctype = get_object_or_404(ContentType, pk=content_type_id)
    parent = get_object_or_404(ctype.model_class(), pk=object_id)

    if request.user.is_staff:
        comments_queryset = parent.comments.all()
    else:
        comments_queryset = parent.comments.visible()

    commenter_ids =  comments_queryset.select_related("user").order_by('-submit_date').values_list('user', flat=True)
    commenters = User.objects.all().filter(id__in=set(commenter_ids))

    template = 'generic/includes/commenters.html'

    s = (int)(""+sIndex)
    l = (int)(""+lIndex)

    sub_commenters = commenters[s:l]

    if s == 0:
        data_href = reverse('fetch_range_commenters_on_obj', kwargs={ 'content_type_id':content_type_id,
                                                                    'object_id':object_id,
                                                                    'sIndex':0,
                                                                    'lIndex': settings.MIN_COMMENTERS_CHUNK})
        return render_to_response(template, {
            'commenters': sub_commenters,
            'is_incremental': False,
            'data_href':data_href,
            'data_chunk':settings.MIN_COMMENTERS_CHUNK
        }, context_instance=RequestContext(request))


    if request.is_ajax():
        context = RequestContext(request)
        context.update({'commenters': sub_commenters,
						'is_incremental': True})
        if sub_commenters:
            ret_data = {
                'html': render_to_string(template, context_instance=context).strip(),
                'success': True
            }
        else:
            ret_data = {
                'success': False
            }

        return HttpResponse(json.dumps(ret_data), mimetype="application/json")

    else:
	    return render_to_response(template, {
	       'commenters': sub_commenters, 
	    }, context_instance=RequestContext(request))

def fetch_comments_on_obj(request, content_type_id, object_id):
    ctype = get_object_or_404(ContentType, pk=content_type_id)
    parent = get_object_or_404(ctype.model_class(), pk=object_id)

    if request.user.is_staff:
        comments_queryset = parent.comments.all()
    else:
        comments_queryset = parent.comments.visible()

    return render_to_response('generic/includes/subcomment.html', {
       'comments_for_thread': comments_queryset, 
    }, context_instance=RequestContext(request))

def fetch_range_comments_on_obj(request, content_type_id, object_id, sIndex, lIndex ):
    ctype = get_object_or_404(ContentType, pk=content_type_id)
    parent = get_object_or_404(ctype.model_class(), pk=object_id)

    if request.user.is_staff:
        comments_queryset = parent.comments.all()
    else:
        comments_queryset = parent.comments.visible()

    s = (int)(""+sIndex)
    l = (int)(""+lIndex)
    
    comments_queryset =  comments_queryset.order_by('-submit_date')[s:l]

    small = request.GET.get("small", None)
    if small:
        return render_to_response('generic/includes/subcomment_small.html', {
           'comments_for_thread': comments_queryset, 
        }, context_instance=RequestContext(request))
    else:
        return render_to_response('generic/includes/subcomment.html', {
            'comments_for_thread': list(comments_queryset)[::-1], 
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

def edit_review(request, review_id, template="generic/includes/write_review.html"):
	if not review_id :
		raise Http404()

	review_obj = Review.objects.get(id=review_id)

	if review_obj and review_obj.user != request.user:
		raise Http404()

	context = RequestContext(request)

	parent_obj = review_obj.content_object

	if request.method == 'POST':
		form = ReviewForm(request, parent_obj, request.POST )

		if form.is_valid():
			url = review_obj.get_absolute_url()
			if is_spam(request, form, url):
				return redirect(url)

			review_obj.comment          = form.cleaned_data['comment']
			review_obj.title            = form.cleaned_data['title']
			review_obj.overall_value    = form.cleaned_data['overall_value']
			review_obj.price_value      = form.cleaned_data['price_value']
			review_obj.variety_value    = form.cleaned_data['variety_value']
			review_obj.quality_value    = form.cleaned_data['quality_value']
			review_obj.service_value    = form.cleaned_data['service_value']
			exchange_value   			= form.cleaned_data['exchange_value']
			"""
			exchange_value is not a required field. Can contain null data as well. Therefore need to handle it seperately.
			"""
			if exchange_value == '':
				review_obj.exchange_value = None
			else:
				review_obj.exchange_value = exchange_value

			review_obj.shop_again       = form.cleaned_data['shop_again']
			review_obj.bought_category  = form.cleaned_data['category']

			try:
				reviewRatingObj                  = RequiredReviewRating.objects.get(commentid=review_obj.id)
				reviewRatingObj.overall_value    = review_obj.overall_value
				reviewRatingObj.price_value      = review_obj.price_value
				reviewRatingObj.variety_value    = review_obj.variety_value
				reviewRatingObj.quality_value    = review_obj.quality_value
				reviewRatingObj.service_value    = review_obj.service_value
				reviewRatingObj.shop_again       = review_obj.shop_again
				reviewRatingObj.save()

				optReviewRatingObj                  = OptionalReviewRating.objects.get(commentid=review_obj.id)
				optReviewRatingObj.exchange_value   = review_obj.service_value
				optReviewRatingObj.save()
				
			except:
				pass

			review_obj.save()

			if request.is_ajax():
				template = 'generic/includes/comment_ajax.html'
				review_page = request.GET.get('reviewpage', '0')

				if review_page == '1':
					template = 'generic/includes/review_ajax.html'

				html = render_to_string(template, { 'comment': review_obj, 'request':request }) 
				res = { 'html': html,
				   		'success':True}
				response = HttpResponse( simplejson.dumps(res), 'application/json' )
			else:
				response = redirect(add_cache_bypass(review_obj.get_absolute_url()))

			return response

		elif form.errors:
			return HttpResponse(simplejson.dumps({"errors": form.errors}), 'application/json' )
	else:        
		data = {
			"comment"           : review_obj.comment,
			"title"             : review_obj.title,
			"overall_value"     : review_obj.overall_value,
			"price_value"       : review_obj.price_value,
			"variety_value"     : review_obj.variety_value,
			"quality_value"     : review_obj.quality_value,
			"service_value"     : review_obj.service_value,
			"exchange_value"    : review_obj.exchange_value,
			"shop_again"        : review_obj.shop_again,
			"category"          : review_obj.bought_category
		}

		form = ReviewForm(request, parent_obj, initial=data)
		form.fields['overall_value'].widget 	= forms.HiddenInput()
		form.fields['price_value'].widget 		= forms.HiddenInput()
		form.fields['variety_value'].widget 	= forms.HiddenInput()
		form.fields['quality_value'].widget 	= forms.HiddenInput()
		form.fields['service_value'].widget 	= forms.HiddenInput()
		form.fields['exchange_value'].widget 	= forms.HiddenInput()

		"""
			Review pages which list all the reviews require a template different than edit review template on store page.
			For such a case reviewpage=1 query parameter should be present.
		"""
		review_page = request.GET.get('reviewpage', '0')
		action_url = reverse("edit_review", kwargs={'review_id':review_id})
		action_url = action_url + '?reviewpage='+review_page

		context = {
				"posted_comment_form": form,
				"action_url":action_url,
				"new_review":False,
				"review_id": review_id
			}
		response =  render(request, template, context)

	return response

def comment_thread_most_liked_view(request, obj, sIndex=0, lIndex=0, template="generic/includes/comments_most_liked.html"):
    """
    Return a list of child comments for the given parent, storing all
    comments in a dict in the context when first called, using parents
    as keys for retrieval on subsequent recursive calls from the
    comments template.
    """
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
    context["sIndex"] = sIndex
    context["lIndex"] = lIndex
    return render(request, template, context)
 
def comment_thread_most_recent_view(request, obj, sIndex=0, lIndex=0, template="generic/includes/comments_most_recent.html"):
    """
    Return a list of child comments for the given parent, storing all
    comments in a dict in the context when first called, using parents
    as keys for retrieval on subsequent recursive calls from the
    comments template.
    """
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
    context["sIndex"] = sIndex
    context["lIndex"] = lIndex
    return render(request, template, context)

 
def comment_thread_default_view(request, obj, template="generic/includes/comments.html"):
    """
    Return a list of child comments for the given parent, storing all
    comments in a dict in the context when first called, using parents
    as keys for retrieval on subsequent recursive calls from the
    comments template.
    """
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

@login_required
def comment_thread_social_view(request, obj, sIndex=0, lIndex=0, template="generic/includes/comments_social.html"):
    """
    Return a list of child comments for the given parent, storing all
    comments in a dict in the context when first called, using parents
    as keys for retrieval on subsequent recursive calls from the
    comments template.
    """
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
    context["sIndex"] = sIndex
    context["lIndex"] = lIndex
    return render(request, template, context)

@login_required
def comment_thread_social_view_level2(request, obj, sIndex=0, lIndex=0, template="generic/includes/comments_social_level2.html"):
    """
    Return a list of child comments for the given parent, storing all
    comments in a dict in the context when first called, using parents
    as keys for retrieval on subsequent recursive calls from the
    comments template.
    """

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
    context["sIndex"] = sIndex
    context["lIndex"] = lIndex
    return render(request, template, context)

def render_review(request, blog_slug, review_id, template="generic/includes/review_page.html"):
    """
    Return a list of child comments for the given parent, storing all
    comments in a dict in the context when first called, using parents
    as keys for retrieval on subsequent recursive calls from the
    comments template.
    """
    review = Review.objects.get(id=review_id)
    context = RequestContext(request)
    blog_post = BlogPost.objects.get(slug=blog_slug)
    return render_to_response('generic/includes/review_page.html', {
       'comment': review, 
       'blog_post': blog_post,
    }, context_instance=context)