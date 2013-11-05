
from django.conf.urls import patterns, url

urlpatterns = patterns("mezzanine.generic.views",
    url("^admin_keywords_submit/$", "admin_keywords_submit",
        name="admin_keywords_submit"),
    url("^rating/$", "rating", name="rating"),
    url("^comment/$", "comment", name="comment"),
    url("^comment_on_review/$", "comment_on_review", name="comment_on_review"),
    url(r'^fetch_comments_on_obj/(?P<content_type_id>\d+)/(?P<object_id>\d+)/$', 'fetch_comments_on_obj', name='fetch_comments_on_obj'),
    url(r'^fetch_commenters_on_obj/(?P<content_type_id>\d+)/(?P<object_id>\d+)/$', 'fetch_commenters_on_obj', name='fetch_commenters_on_obj'),
    url(r'^fetch_range_commenters_on_obj/(?P<content_type_id>\d+)/(?P<object_id>\d+)/(?P<sIndex>\d+)/(?P<lIndex>\d+)/$', 'fetch_range_commenters_on_obj', name='fetch_range_commenters_on_obj'),
    url("^view/(?P<username>.*)$", "commentProfile", name="commentProfile"),
   	url("^comment_thread_most_liked_view/(?P<obj>.*)$", "comment_thread_most_liked_view", name="comment_thread_most_liked_view"),
   	url("^comment_thread_most_recent_view/(?P<obj>.*)$", "comment_thread_most_recent_view", name="comment_thread_most_recent_view"),
   	url("^comment_thread_default_view/(?P<obj>.*)$", "comment_thread_default_view", name="comment_thread_default_view"),
   	url("^comment_thread_social_view/(?P<obj>.*)$", "comment_thread_social_view", name="comment_thread_social_view"),
    url("^comment_thread_social_view_level2/(?P<obj>.*)$", "comment_thread_social_view_level2", name="comment_thread_social_view_level2"),
    url(r'^edit/review/(?P<review_id>\d+)/$', 'edit_review', name='edit_review'),
    url(r'^review/(?P<blog_slug>\w+)/(?P<review_id>\d+)/$', 'render_review', name='render_review'),
    url(r'^new/review/(?P<content_type_id>\d+)/(?P<object_id>\d+)/$', "write_review", name="write_review"),
    url(r'^comments_subset/(?P<content_type_id>\d+)/(?P<object_id>\d+)/(?P<sIndex>\d+)/(?P<lIndex>\d+)/$','fetch_range_comments_on_obj', name='fetch_range_comments_on_obj'),
)
