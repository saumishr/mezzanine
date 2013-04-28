
from django.conf.urls import patterns, url

urlpatterns = patterns("mezzanine.generic.views",
    url("^admin_keywords_submit/$", "admin_keywords_submit",
        name="admin_keywords_submit"),
    url("^rating/$", "rating", name="rating"),
    url("^comment/$", "comment", name="comment"),
    url("^view/(?P<username>.*)$", "commentProfile", name="commentProfile"),
   	url("^comment_thread_most_liked_view/(?P<obj>.*)$", "comment_thread_most_liked_view", name="comment_thread_most_liked_view"),
   	url("^comment_thread_most_recent_view/(?P<obj>.*)$", "comment_thread_most_recent_view", name="comment_thread_most_recent_view"),
   	url("^comment_thread_default_view/(?P<obj>.*)$", "comment_thread_default_view", name="comment_thread_default_view"),
   	url("^comment_thread_social_view/(?P<obj>.*)$", "comment_thread_social_view", name="comment_thread_social_view"),
	url("^comment_thread_social_view_level2/(?P<obj>.*)$", "comment_thread_social_view_level2", name="comment_thread_social_view_level2"),
)
