from datetime import datetime

from django.db.models import Count, Q

from mezzanine.blog.forms import BlogPostForm
from mezzanine.blog.models import BlogPost, BlogCategory, BlogParentCategory
from mezzanine.generic.models import Keyword
from mezzanine import template
from mezzanine.utils.models import get_user_model
from django.template.defaultfilters import slugify
from django.utils import simplejson

User = get_user_model()

register = template.Library()

@register.as_tag
def blog_months(*args):
    """
    Put a list of dates for blog posts into the template context.
    """
    dates = BlogPost.objects.published().values_list("publish_date", flat=True)
    date_dicts = [{"date": datetime(d.year, d.month, 1)} for d in dates]
    month_dicts = []
    for date_dict in date_dicts:
        if date_dict not in month_dicts:
            month_dicts.append(date_dict)
    for i, date_dict in enumerate(month_dicts):
        month_dicts[i]["post_count"] = date_dicts.count(date_dict)
    return month_dicts


@register.as_tag
def blog_categories(*args):
    """
    Put a list of categories for blog posts into the template context.
    """
    posts = BlogPost.objects.published()
    categories = BlogCategory.objects.filter(blogposts__in=posts)
    return list(categories.annotate(post_count=Count("blogposts")))

@register.as_tag
def blog_categories_abs(*args):
    """
    Put a list of categories for blog posts into the template context.
    """
    categories = BlogCategory.objects.all()
    return list(categories)

@register.assignment_tag
def blog_categories_json(*args):
    """
    Put a list of categories for blog posts into the template context.
    """
    parent_categories = BlogParentCategory.objects.all()
    categories = {}
    for parent_category in parent_categories:
        sub_categories = BlogCategory.objects.all().filter(parent_category=parent_category)
        categories[parent_category.slug] = [sub_category.slug for sub_category in sub_categories]
    return  simplejson.dumps(categories)


@register.as_tag
def blog_parentcategories_abs(*args):
    """
    Put a list of categories for blog posts into the template context.
    """
    parent_categories = BlogParentCategory.objects.all()
    return list(parent_categories)

@register.as_tag
def blog_subcategories(parent_category_slug):
    try:
        parent_category = BlogParentCategory.objects.get(slug=slugify(parent_category_slug))
    except BlogParentCategory.DoesNotExist:
        return ''

    sub_categories = None
    if parent_category:
        sub_categories = BlogCategory.objects.all().filter(parent_category=parent_category)
        return list(sub_categories)
    return ''

@register.as_tag
def blog_subcategories_for_blog(blog):
    """
    Put a list of categories for blog posts into the template context.
    """
    sub_categories = blog.categories.all() 
    return list(sub_categories)

@register.as_tag
def blog_authors(*args):
    """
    Put a list of authors (users) for blog posts into the template context.
    """
    blog_posts = BlogPost.objects.published()
    authors = User.objects.filter(blogposts__in=blog_posts)
    return list(authors.annotate(post_count=Count("blogposts")))


@register.as_tag
def blog_recent_posts(limit=5, tag=None, username=None, category=None):
    """
    Put a list of recently published blog posts into the template
    context. A tag title or slug, category title or slug or author's
    username can also be specified to filter the recent posts returned.

    Usage::

        {% blog_recent_posts 5 as recent_posts %}
        {% blog_recent_posts limit=5 tag="django" as recent_posts %}
        {% blog_recent_posts limit=5 category="python" as recent_posts %}
        {% blog_recent_posts 5 username=admin as recent_posts %}

    """
    blog_posts = BlogPost.objects.published().select_related("user")
    title_or_slug = lambda s: Q(title=s) | Q(slug=s)
    if tag is not None:
        try:
            tag = Keyword.objects.get(title_or_slug(tag))
            blog_posts = blog_posts.filter(keywords__in=tag.assignments.all())
        except Keyword.DoesNotExist:
            return []
    if category is not None:
        try:
            category = BlogCategory.objects.get(title_or_slug(category))
            blog_posts = blog_posts.filter(categories=category)
        except BlogCategory.DoesNotExist:
            return []
    if username is not None:
        try:
            author = User.objects.get(username=username)
            blog_posts = blog_posts.filter(user=author)
        except User.DoesNotExist:
            return []
    return list(blog_posts[:limit])


@register.inclusion_tag("admin/includes/quick_blog.html", takes_context=True)
def quick_blog(context):
    """
    Admin dashboard tag for the quick blog form.
    """
    context["form"] = BlogPostForm()
    return context
