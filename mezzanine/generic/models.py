
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.generic import GenericForeignKey
from django.db import models
from django.template.defaultfilters import truncatewords_html
from django.utils.translation import ugettext, ugettext_lazy as _

from mezzanine.generic.fields import RatingField
from mezzanine.generic.managers import CommentManager, KeywordManager
from mezzanine.core.models import Slugged, Orderable
from mezzanine.conf import settings
from mezzanine.utils.models import get_user_model_name
from mezzanine.utils.sites import current_site_id
from mezzanine.generic.fields import CommentsField


class ThreadedComment(Comment):
    """
    Extend the ``Comment`` model from ``django.contrib.comments`` to
    add comment threading. ``Comment`` provides its own site foreign key,
    so we can't inherit from ``SiteRelated`` in ``mezzanine.core``, and
    therefore need to set the site on ``save``. ``CommentManager``
    inherits from Mezzanine's ``CurrentSiteManager``, so everything else
    site related is already provided.
    """

    by_author = models.BooleanField(_("By the blog author"), default=False)
    replied_to = models.ForeignKey("self", null=True, editable=False,
                                   related_name="repliedto")
    rating = RatingField(verbose_name=_("Rating"))

    comments = CommentsField(verbose_name=_("Comments"))
    objects = CommentManager()

    class Meta:
        verbose_name = _("Comment")
        verbose_name_plural = _("Comments")

    def get_absolute_url(self):
        """
        Use the URL for the comment's content object, with a URL hash
        appended that references the individual comment.
        """
        url = self.content_object.get_absolute_url()
        return "%s#comment-%s" % (url, self.id)

    def save(self, *args, **kwargs):
        """
        Set the current site ID, and ``is_public`` based on the setting
        ``COMMENTS_DEFAULT_APPROVED``.
        """
        if not self.id:
            self.is_public = settings.COMMENTS_DEFAULT_APPROVED
            self.site_id = current_site_id()
        super(ThreadedComment, self).save(*args, **kwargs)

    ################################
    # Admin listing column methods #
    ################################

    def intro(self):
        return truncatewords_html(self.comment, 20)
    intro.short_description = _("Comment")

    def avatar_link(self):
        from mezzanine.core.templatetags.mezzanine_tags import gravatar_url
        vars = (self.user_email, gravatar_url(self.email), self.user_name)
        return ("<a href='mailto:%s'><img style='vertical-align:middle; "
                "margin-right:3px;' src='%s' />%s</a>" % vars)
    avatar_link.allow_tags = True
    avatar_link.short_description = _("User")

    def admin_link(self):
        return "<a href='%s'>%s</a>" % (self.get_absolute_url(),
                                        ugettext("View on site"))
    admin_link.allow_tags = True
    admin_link.short_description = ""

    # Exists for backward compatibility when the gravatar_url template
    # tag which took the email address hash instead of the email address.
    @property
    def email_hash(self):
        return self.email

class Review(ThreadedComment):
    overall_value = models.IntegerField(_("Overall"))
    price_value = models.IntegerField(_("Price"))
    variety_value = models.IntegerField(_("Variety"))
    quality_value = models.IntegerField(_("Quality"))
    service_value = models.IntegerField(_("Customer Service"))
    exchange_value = models.IntegerField(_("Exchange Experience"), null = True)
    bought_category = models.TextField(_("Bought"))
    
    objects = CommentManager()
    
    class Meta:
        verbose_name = _("Review")
        verbose_name_plural = _("Review")

class Keyword(Slugged):
    """
    Keywords/tags which are managed via a custom JavaScript based
    widget in the admin.
    """

    objects = KeywordManager()

    class Meta:
        verbose_name = _("Keyword")
        verbose_name_plural = _("Keywords")


class AssignedKeyword(Orderable):
    """
    A ``Keyword`` assigned to a model instance.
    """

    keyword = models.ForeignKey("Keyword", verbose_name=_("Keyword"),
                                related_name="assignments")
    content_type = models.ForeignKey("contenttypes.ContentType")
    object_pk = models.IntegerField()
    content_object = GenericForeignKey("content_type", "object_pk")

    class Meta:
        order_with_respect_to = "content_object"

    def __unicode__(self):
        return unicode(self.keyword)

class RequiredReviewRating(models.Model):
    """
    A rating that can be given to a piece of content.
    """
    overall_value = models.IntegerField(_("Overall Value"))
    price_value = models.IntegerField(_("Price Value"))
    variety_value = models.IntegerField(_("Variety Value"))
    quality_value = models.IntegerField(_("Quality Value"))
    service_value = models.IntegerField(_("Service Value"))
    rating_date = models.DateTimeField(_("Required Review Rating date"),
        auto_now_add=True, null=True)
    content_type = models.ForeignKey("contenttypes.ContentType")
    object_pk = models.IntegerField()
    content_object = GenericForeignKey("content_type", "object_pk")
    user = models.ForeignKey(get_user_model_name(), verbose_name=_("Required Rater"),
        null=True, related_name="%(class)ss")
    commentid = models.PositiveIntegerField(_("Comment Id"))
    
    class Meta:
        verbose_name = _("RequiredReviewRating")
        verbose_name_plural = _("RequiredReviewRatings")

    def save(self, *args, **kwargs):
        """
        Validate that the rating falls between the min and max values.
        """
        valid = map(str, settings.RATINGS_RANGE)
        if str(self.overall_value) not in valid:
            raise ValueError("Invalid Overall rating. %s is not in %s" % (self.overall_value,
                ", ".join(valid)))
        if str(self.price_value) not in valid:
            raise ValueError("Invalid Price rating. %s is not in %s" % (self.price_value,
                ", ".join(valid)))
        if str(self.variety_value) not in valid:
            raise ValueError("Invalid Variety rating. %s is not in %s" % (self.variety_value,
                ", ".join(valid)))
        if str(self.quality_value) not in valid:
            raise ValueError("Invalid Quality rating. %s is not in %s" % (self.quality_value,
                ", ".join(valid)))
        if str(self.service_value) not in valid:
            raise ValueError("Invalid Service rating. %s is not in %s" % (self.service_value,
                ", ".join(valid)))
        super(RequiredReviewRating, self).save(*args, **kwargs)

class OptionalReviewRating(models.Model):
    """
    A rating that can be given to a piece of content.
    """

    exchange_value = models.IntegerField(_("Exchange Value"))
    rating_date = models.DateTimeField(_("Optional Review Rating date"),
        auto_now_add=True, null=True)
    content_type = models.ForeignKey("contenttypes.ContentType")
    object_pk = models.IntegerField()
    content_object = GenericForeignKey("content_type", "object_pk")
    user = models.ForeignKey(get_user_model_name(), verbose_name=_("Optional Rater"),
        null=True, related_name="%(class)ss")
    commentid = models.PositiveIntegerField(_("Comment Id"))

    class Meta:
        verbose_name = _("OptionalReviewRating")
        verbose_name_plural = _("OptionalReviewRatings")

    def save(self, *args, **kwargs):
        """
        Validate that the rating falls between the min and max values.
        """
        valid = map(str, settings.RATINGS_RANGE)
        if str(self.exchange_value) not in valid:
            raise ValueError("Invalid Exchange rating. %s is not in %s" % (self.exchange_value,
                ", ".join(valid)))
        super(OptionalReviewRating, self).save(*args, **kwargs)

class Rating(models.Model):
    """
    A rating that can be given to a piece of content.
    """

    value = models.IntegerField(_("Value"))
    rating_date = models.DateTimeField(_("Rating date"),
        auto_now_add=True, null=True)
    content_type = models.ForeignKey("contenttypes.ContentType")
    object_pk = models.IntegerField()
    content_object = GenericForeignKey("content_type", "object_pk")
    user = models.ForeignKey(get_user_model_name(), verbose_name=_("Rater"),
        null=True, related_name="%(class)ss")

    class Meta:
        verbose_name = _("Rating")
        verbose_name_plural = _("Ratings")

    def save(self, *args, **kwargs):
        """
        Validate that the rating falls between the min and max values.
        """
        valid = map(str, settings.RATINGS_RANGE)
        if str(self.value) not in valid:
            raise ValueError("Invalid rating. %s is not in %s" % (self.value,
                ", ".join(valid)))
        super(Rating, self).save(*args, **kwargs)
