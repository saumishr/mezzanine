
from django.conf.urls import patterns, url

urlpatterns = patterns("mezzanine.generic.views",
    url("^admin_keywords_submit/$", "admin_keywords_submit",
        name="admin_keywords_submit"),
    url("^rating/$", "rating", name="rating"),
    url("^comment/$", "comment", name="comment"),
    url("^comment_on_review/$", "comment_on_review", name="comment_on_review"),
    url(r'^comments/object/(?P<content_type_id>\d+)/(?P<object_id>\d+)/$', 'fetch_comments_on_obj', name='fetch_comments_on_obj'),
    url(r'^comments/object/(?P<content_type_id>\d+)/(?P<object_id>\d+)/users/$', 'fetch_commenters_on_obj', name='fetch_commenters_on_obj'),
    url(r'^comments/object/(?P<content_type_id>\d+)/(?P<object_id>\d+)/users/range/(?P<sIndex>\d+)/(?P<lIndex>\d+)/$', 'fetch_range_commenters_on_obj', name='fetch_range_commenters_on_obj'),
    url(r'^view/(?P<username>.*)$', "commentProfile", name="commentProfile"),
   	url(r'^comments/object/liked/(?P<object_id>\d+)/$', "comment_thread_most_liked_view", name="comment_thread_most_liked_view"),
   	url(r'^comments/object/recent/(?P<object_id>\d+)/$', "comment_thread_most_recent_view", name="comment_thread_most_recent_view"),
   	url(r'^comments/object/default/(?P<object_id>\d+)$', "comment_thread_default_view", name="comment_thread_default_view"),
   	url(r'^comments/object/social/(?P<object_id>\d+)/$', "comment_thread_social_view", name="comment_thread_social_view"),
    url(r'^comments/object/social-deep/(?P<object_id>\d+)/$', "comment_thread_social_view_level2", name="comment_thread_social_view_level2"),
    url(r'^review/(?P<review_id>\d+)/edit/$', 'edit_review', name='edit_review'),
    url(r'^review/(?P<blog_slug>\w+)/(?P<review_id>\d+)/$', 'render_review', name='render_review'),
    url(r'^review/new/(?P<content_type_id>\d+)/(?P<object_id>\d+)/$', "write_review", name="write_review"),
    url(r'^comments/object/(?P<content_type_id>\d+)/(?P<object_id>\d+)/range/(?P<sIndex>\d+)/(?P<lIndex>\d+)/$','fetch_range_comments_on_obj', name='fetch_range_comments_on_obj'),
)
