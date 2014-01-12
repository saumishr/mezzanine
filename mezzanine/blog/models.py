from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save

from mezzanine.conf import settings
from mezzanine.core.fields import FileField
from mezzanine.core.models import Displayable, Ownable, RichText, Slugged, UniqueSlugged
from mezzanine.generic.fields import CommentsField, RatingField, ReviewsField, RequiredReviewRatingField, OptionalReviewRatingField
from mezzanine.utils.models import AdminThumbMixin, upload_to
from django.db import models
from follow import utils
from actstream import actions

class BlogPost(Displayable, Ownable, RichText, AdminThumbMixin):
    """
    A blog post.
    """

    categories = models.ManyToManyField("BlogCategory",
                                        verbose_name=_("Categories"),
                                        blank=True, related_name="blogposts")

    allow_comments = models.BooleanField(verbose_name=_("Allow comments"),
                                         default=True)

    comments = ReviewsField(verbose_name=_("Reviews"))
    rating = RatingField(verbose_name=_("Rating"))
    requiredreviewrating = RequiredReviewRatingField(verbose_name=_("RequiredReviewRating"))
    optionalreviewrating = OptionalReviewRatingField(verbose_name=_("OptionalReviewRating"))
    featured_image = FileField(verbose_name=_("Featured Image"),
        upload_to=upload_to("blog.BlogPost.featured_image", "blog"),
        format="Image", max_length=255, null=True, blank=True)
    related_posts = models.ManyToManyField("self",
                                 verbose_name=_("Related posts"), blank=True)

    admin_thumb_field = "featured_image"
    num_images    = models.PositiveIntegerField(verbose_name="Photos Uploaded", default=0)
    web_url = models.URLField(verify_exists=True, max_length=200, null=True, blank=True)

    class Meta:
        verbose_name = _("Blog post")
        verbose_name_plural = _("Blog posts")
        ordering = ("-publish_date",)

    @models.permalink
    def get_absolute_url(self):
        """
        URLs for blog posts can either be just their slug, or prefixed
        with a portion of the post's publish date, controlled by the
        setting ``BLOG_URLS_DATE_FORMAT``, which can contain the value
        ``year``, ``month``, or ``day``. Each of these maps to the name
        of the corresponding urlpattern, and if defined, we loop through
        each of these and build up the kwargs for the correct urlpattern.
        The order which we loop through them is important, since the
        order goes from least granualr (just year) to most granular
        (year/month/day).
        """
        url_name = "blog_post_detail"
        kwargs = {"slug": self.slug}
        date_parts = ("year", "month", "day")
        if settings.BLOG_URLS_DATE_FORMAT in date_parts:
            url_name = "blog_post_detail_%s" % settings.BLOG_URLS_DATE_FORMAT
            for date_part in date_parts:
                date_value = str(getattr(self.publish_date, date_part))
                if len(date_value) == 1:
                    date_value = "0%s" % date_value
                kwargs[date_part] = date_value
                if date_part == settings.BLOG_URLS_DATE_FORMAT:
                    break
        return (url_name, (), kwargs)

    # These methods are deprecated wrappers for keyword and category
    # access. They existed to support Django 1.3 with prefetch_related
    # not existing, which was therefore manually implemented in the
    # blog list views. All this is gone now, but the access methods
    # still exist for older templates.

    def category_list(self):
        from warnings import warn
        warn("blog_post.category_list in templates is deprecated"
             "use blog_post.categories.all which are prefetched")
        return getattr(self, "_categories", self.categories.all())

    def keyword_list(self):
        from warnings import warn
        warn("blog_post.keyword_list in templates is deprecated"
             "use the keywords_for template tag, as keywords are prefetched")
        try:
            return self._keywords
        except AttributeError:
            keywords = [k.keyword for k in self.keywords.all()]
            setattr(self, "_keywords", keywords)
            return self._keywords

utils.register(BlogPost)

class BlogCategory(Slugged):
    """
    A category for grouping blog posts into a series.
    """
    parent_category = models.ManyToManyField("BlogParentCategory", null=True,
                                   related_name="blog_parent_category")
    class Meta:
        verbose_name = _("Blog Category")
        verbose_name_plural = _("Blog Categories")
        ordering = ("title",)

    @models.permalink
    def get_absolute_url(self):
        url_name = "get_vendors"
        parent_category_loc = self.parent_category.all()[0]
        kwargs = {"parent_category_slug": parent_category_loc.slug, "sub_category_slug": self.slug}
        return (url_name, (), kwargs)


class BlogParentCategory(UniqueSlugged):
    """
    A category for grouping blog posts into a series.
    """

    class Meta:
        verbose_name = _("Blog ParentCategory")
        verbose_name_plural = _("Blog ParentCategories")
        ordering = ("title",)

    @models.permalink
    def get_absolute_url(self):
        url_name = "get_vendors"
        kwargs = {"parent_category_slug": self.slug, "sub_category_slug": "all"}
        return (url_name, (), kwargs)


def blog_post_saved(sender, created, **kwargs):
    from django.http import Http404, HttpResponse
    from django.utils import simplejson

    if created:
        obj = kwargs['instance']
        if obj:
            actions.follow(obj.user, obj, send_action=False, actor_only=False) 

post_save.connect(blog_post_saved, sender=BlogPost)
