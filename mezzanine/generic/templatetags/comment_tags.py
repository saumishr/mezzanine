
from collections import defaultdict

from django.core.urlresolvers import reverse
from django.template.defaultfilters import linebreaksbr, urlize

from mezzanine import template
from mezzanine.conf import settings
from mezzanine.generic.forms import ThreadedCommentForm
from mezzanine.generic.forms import ReviewForm
from mezzanine.generic.models import ThreadedComment, Review
from mezzanine.blog.models import BlogPost

from django.contrib.contenttypes.models import ContentType
from voting.models import Vote
from django.contrib.comments.models import Comment

from django.core.urlresolvers import reverse
from django.template import TemplateSyntaxError, Node, Variable
from django.contrib.contenttypes.models import ContentType

register = template.Library()


@register.inclusion_tag("generic/includes/comments.html", takes_context=True)
def comments_for(context, obj):
    """
    Provides a generic context variable name for the object that
    comments are being rendered for.
    """
    form = ReviewForm(context["request"], obj)
    try:
        context["posted_comment_form"]
    except KeyError:
        context["posted_comment_form"] = form
    context["unposted_comment_form"] = form
    context["comment_url"] = reverse("comment")
    context["object_for_comments"] = obj
    return context

@register.inclusion_tag("generic/includes/comments.html", takes_context=True)
def comments_for_review(context, obj):
    """
    Provides a generic context variable name for the object that
    comments are being rendered for.
    """
    form = ThreadedCommentForm(context["request"], obj)
    form.fields['comment'].widget.attrs['class'] = 'comment_on_review'
    form.fields['comment'].widget.attrs['placeholder'] = 'Write a comment...'
    form.fields['comment'].label = "comment"
    context["posted_comment_form"] = form
    context["unposted_comment_form"] = form
    context["comment_url"] = reverse("comment_on_review")
    context["object_for_comments"] = obj
    return context

@register.inclusion_tag("generic/includes/comment.html", takes_context=True)
def comment_thread(context, parent):
    """
    Return a list of child comments for the given parent, storing all
    comments in a dict in the context when first called, using parents
    as keys for retrieval on subsequent recursive calls from the
    comments template.
    """
    if "all_comments" not in context:
        comments = defaultdict(list)
        if "request" in context and context["request"].user.is_staff:
            comments_queryset = parent.comments.all()
        else:
            comments_queryset = parent.comments.visible()
        for comment in comments_queryset.select_related("user"):
            comments[comment.replied_to_id].append(comment)
        context["all_comments"] = comments
    parent_id = parent.id if isinstance(parent, Review) else None
    try:
        replied_to = int(context["request"].POST["replied_to"])
    except KeyError:
        replied_to = 0
    context.update({
        "comments_for_thread": context["all_comments"].get(parent_id, []),
        "no_comments": parent_id is None and not context["all_comments"],
        "replied_to": replied_to,
    })
    return context

@register.inclusion_tag("generic/includes/comment.html", takes_context=True)
def comment_thread_most_recent(context, parent):
    """
    Return a list of child comments for the given parent, storing all
    comments in a dict in the context when first called, using parents
    as keys for retrieval on subsequent recursive calls from the
    comments template.
    """
    import operator
    if "all_comments" not in context:
        comments = defaultdict(list)
        if "request" in context and context["request"].user.is_staff:
            comments_queryset = parent.comments.all()
        else:
            comments_queryset = parent.comments.visible()

        commentsList = comments_queryset.order_by('-submit_date')
        for comment in commentsList.select_related("user"):
            comments[comment.replied_to_id].append(comment)
  
        context["all_comments"] = comments

    parent_id = parent.id if isinstance(parent, Review) else None
    
    try:
        replied_to = int(context["request"].POST["replied_to"])
    except KeyError:
        replied_to = 0
    context.update({
        "comments_for_thread": context["all_comments"].get(parent_id, []),
        "no_comments": parent_id is None and not comments,
        "replied_to": replied_to,
    })
    return context


@register.inclusion_tag("generic/includes/comment.html", takes_context=True)
def comment_thread_most_liked(context, parent):
    """
    Return a list of child comments for the given parent, storing all
    comments in a dict in the context when first called, using parents
    as keys for retrieval on subsequent recursive calls from the
    comments template.
    """
    import operator
    from django.db.models import Count, Min
    if "all_comments" not in context:
        comments = defaultdict(list)
        if "request" in context and context["request"].user.is_staff:
            comments_queryset = parent.comments.all()
        else:
            comments_queryset = parent.comments.visible()

        model_type = ContentType.objects.get_for_model(Review)
        table_name = Comment._meta.db_table

        commentsList = comments_queryset.extra(select={
            'score': 'SELECT COALESCE(SUM(vote),0) FROM %s WHERE content_type_id=%d AND object_id=%s.id' % (Vote._meta.db_table, int(model_type.id), table_name)
        }).order_by('-score',)

        for comment in commentsList.select_related("user"):
            comments[comment.replied_to_id].append(comment)
 
        context["all_comments"] = comments
    parent_id = parent.id if isinstance(parent, Review) else None
    try:
        replied_to = int(context["request"].POST["replied_to"])
    except KeyError:
        replied_to = 0
    context.update({
        "comments_for_thread": context["all_comments"].get(parent_id, []),
        "no_comments": parent_id is None and not context["all_comments"],
        "replied_to": replied_to,
    })
    return context

@register.inclusion_tag("generic/includes/comment.html", takes_context=True)
def comment_thread_social(context, parent):
    """
    Return a list of child comments for the given parent, storing all
    comments in a dict in the context when first called, using parents
    as keys for retrieval on subsequent recursive calls from the
    comments template.
    """
    from social_auth.models import UserSocialAuth
    from social_friends_finder.models import SocialFriendList
    from django.http import HttpResponse

    if "all_comments" not in context:
        comments = defaultdict(list)
        if "request" in context and context["request"].user.is_staff:
            comments_queryset = parent.comments.all()
        else:
            comments_queryset = parent.comments.visible()

        comments_queryset = comments_queryset.order_by('-submit_date')

        #user_social_auth_list = context["request"].user.social_auth.filter(provider="facebook")
        #if not user_social_auth_list:
        #    user_social_auth_list = context["request"].user.social_auth.filter(provider="twitter")
        #if user_social_auth_list:
        #    user_social_auth = user_social_auth_list[0]    
        #    friends = SocialFriendList.objects.existing_social_friends(context["request"].user.social_auth.filter(provider="facebook")[0])
        #    for comment in comments_queryset.select_related("user"):
        #        if comment.user in friends:
        #            comments[comment.replied_to_id].append(comment)
        
        friends = context["request"].user.relationships.following()
        for comment in comments_queryset.select_related("user"):
            if comment.user in friends:
                comments[comment.replied_to_id].append(comment)

        context["all_comments"] = comments
    parent_id = parent.id if isinstance(parent, Review) else None
    try:
        replied_to = int(context["request"].POST["replied_to"])
    except KeyError:
        replied_to = 0
    context.update({
        "comments_for_thread": context["all_comments"].get(parent_id, []),
        "no_comments": parent_id is None and not context["all_comments"],
        "replied_to": replied_to,
    })
    return context

@register.inclusion_tag("generic/includes/comment.html", takes_context=True)
def comment_thread_social_level2(context, parent):
    """
    Return a list of child comments for the given parent, storing all
    comments in a dict in the context when first called, using parents
    as keys for retrieval on subsequent recursive calls from the
    comments template.
    """
    from social_auth.models import UserSocialAuth
    from social_friends_finder.models import SocialFriendList
    from django.http import HttpResponse
    from itertools import chain
    from operator import attrgetter
    from django.core.cache import cache

    if "all_comments" not in context:
        comments = defaultdict(list)
        if "request" in context and context["request"].user.is_staff:
            comments_queryset = parent.comments.all()
        else:
            comments_queryset = parent.comments.visible()

        #user_social_auth_list = context["request"].user.social_auth.filter(provider="facebook")
        #if not user_social_auth_list:
        #    user_social_auth_list = context["request"].user.social_auth.filter(provider="twitter")
        #if user_social_auth_list:
        #    user_social_auth = user_social_auth_list[0]
        #    if user_social_auth:
        #        friends_of_friends = cache.get(user_social_auth.user.username+"SocialFriendListLevel2")
        #        if  not friends_of_friends:            
        #            friends = SocialFriendList.objects.existing_social_friends(context["request"].user.social_auth.filter(provider="facebook")[0])
        #            friends_of_friends = list(friends)
        #            for friend in friends:
        #                friends_level2 = SocialFriendList.objects.existing_social_friends(friend.social_auth.filter(provider="facebook")[0])
        #                friends_of_friends = list(chain(friends_of_friends, friends_level2))
        #            cache.set(user_social_auth.user.username+"SocialFriendListLevel2", friends_of_friends)
        friends_of_friends = set()

        friends = context["request"].user.relationships.following()
        for friend in friends:
            friends_of_friends.add(friend)
            friends_level2 = friend.relationships.following()
            for friend_level2 in friends_level2:
                friends_of_friends.add(friend_level2)

        comments_queryset = comments_queryset.order_by('-submit_date')

        for comment in comments_queryset.select_related("user"):
                if comment.user in friends_of_friends:
                        comments[comment.replied_to_id].append(comment)
 
        context["all_comments"] = comments
    parent_id = parent.id if isinstance(parent, Review) else None
    try:
        replied_to = int(context["request"].POST["replied_to"])
    except KeyError:
        replied_to = 0
    context.update({
        "comments_for_thread": context["all_comments"].get(parent_id, []),
        "no_comments": parent_id is None and not context["all_comments"],
        "replied_to": replied_to,
    })
    return context


@register.inclusion_tag("admin/includes/recent_comments.html",
    takes_context=True)
def recent_comments(context):
    """
    Dashboard widget for displaying recent comments.
    """
    latest = context["settings"].COMMENTS_NUM_LATEST
    comments = ThreadedComment.objects.all().select_related("user")
    context["comments"] = comments.order_by("-id")[:latest]
    return context

@register.inclusion_tag("admin/includes/recent_comments.html",
    takes_context=True)
def recent_reviews(context):
    """
    Dashboard widget for displaying recent comments.
    """
    comments = []
    latest = context["settings"].COMMENTS_NUM_LATEST
    comments_queryset = ThreadedComment.objects.all()
    for comment in comments_queryset.select_related("user"):
        if isinstance(comment.content_object, BlogPost):
            comments.append(comment) 
    context["comments"] = comments
    return context

@register.simple_tag(name='comment_count_on_object')
def get_number_of_comments_on_obj(object):
    comments_queryset = None
    if object:
        comments_queryset = object.comments.visible().select_related("user")
    return len(comments_queryset)    

@register.filter
def comment_filter(comment_text):
    """
    Passed comment text to be rendered through the function defined
    by the ``COMMENT_FILTER`` setting. If no function is defined
    (the default), Django's ``linebreaksbr`` and ``urlize`` filters
    are used.
    """
    filter_func = settings.COMMENT_FILTER
    if not filter_func:
        filter_func = lambda s: linebreaksbr(urlize(s))
    return filter_func(comment_text)

@register.filter
def get_class_name(value):
    return value.__class__.__name__

@register.tag
def comments_for_obj_url(parser, token):
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError("Accepted format {% comments_for_obj_url [instance] %}")
    else:
        return CommentsForObjURL(bits[1])

class CommentsForObjURL(Node):
    def __init__(self, obj):
        self.obj = Variable(obj)

    def render(self, context):
        obj_instance = self.obj.resolve(context)
        content_type = ContentType.objects.get_for_model(obj_instance).pk
        return reverse('fetch_comments_on_obj', kwargs={'content_type_id': content_type, 'object_id': obj_instance.pk })

@register.tag
def get_commenters_url(parser, token):
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError("Accepted format {% comments_for_obj_url [instance] %}")
    else:
        return GetCommentersForObjURL(bits[1])

class GetCommentersForObjURL(Node):
    def __init__(self, obj):
        self.obj = Variable(obj)

    def render(self, context):
        obj_instance = self.obj.resolve(context)
        content_type = ContentType.objects.get_for_model(obj_instance).pk
        return reverse('fetch_commenters_on_obj', kwargs={'content_type_id': content_type, 'object_id': obj_instance.pk })

@register.inclusion_tag("generic/includes/render_comment.html", takes_context=True)
def render_comment(context, comment):
    context.update({
        "comment": comment,
    })
    return context
