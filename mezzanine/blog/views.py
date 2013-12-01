from calendar import month_name

from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import simplejson
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

from mezzanine.blog.models import BlogPost, BlogCategory, BlogParentCategory
from mezzanine.blog.feeds import PostsRSS, PostsAtom
from mezzanine.conf import settings
from mezzanine.generic.models import Keyword
from mezzanine.utils.views import render, paginate
from mezzanine.utils.models import get_user_model
import urlparse

User = get_user_model()


def blog_post_list(request, tag=None, year=None, month=None, username=None,
                   category=None, template="blog/blog_post_list.html"):
    """
    Display a list of blog posts that are filtered by tag, year, month,
    author or category. Custom templates are checked for using the name
    ``blog/blog_post_list_XXX.html`` where ``XXX`` is either the
    category slug or author's username if given.
    """
    settings.use_editable()
    templates = []
    blog_posts = BlogPost.objects.published(for_user=request.user)
    if tag is not None:
        tag = get_object_or_404(Keyword, slug=tag)
        blog_posts = blog_posts.filter(keywords__in=tag.assignments.all())
    if year is not None:
        blog_posts = blog_posts.filter(publish_date__year=year)
        if month is not None:
            blog_posts = blog_posts.filter(publish_date__month=month)
            month = month_name[int(month)]
    if category is not None:
        category = get_object_or_404(BlogCategory, slug=category)
        blog_posts = blog_posts.filter(categories=category)
        templates.append(u"blog/blog_post_list_%s.html" %
                          unicode(category.slug))
    author = None
    if username is not None:
        author = get_object_or_404(User, username=username)
        blog_posts = blog_posts.filter(user=author)
        templates.append(u"blog/blog_post_list_%s.html" % username)

    prefetch = ("categories", "keywords__keyword")
    blog_posts = blog_posts.select_related("user").prefetch_related(*prefetch)
    blog_posts = paginate(blog_posts, request.GET.get("page", 1),
                          settings.BLOG_POST_PER_PAGE,
                          settings.MAX_PAGING_LINKS)
    context = {"blog_posts": blog_posts, "year": year, "month": month,
               "tag": tag, "category": category, "author": author}
    templates.append(template)
    return render(request, templates, context)


def blog_post_detail(request, slug, year=None, month=None, day=None,
                     template="blog/blog_post_detail.html"):
    """. Custom templates are checked for using the name
    ``blog/blog_post_detail_XXX.html`` where ``XXX`` is the blog
    posts's slug.
    """
    blog_posts = BlogPost.objects.published(
                                     for_user=request.user).select_related()
    blog_post = get_object_or_404(blog_posts, slug=slug)
    context = {"blog_post": blog_post, "editable_obj": blog_post}
    templates = [u"blog/blog_post_detail_%s.html" % unicode(slug), template]
    return render(request, templates, context)


def blog_post_feed(request, format, **kwargs):
    """
    Blog posts feeds - maps format to the correct feed view.
    """
    try:
        return {"rss": PostsRSS, "atom": PostsAtom}[format](**kwargs)(request)
    except KeyError:
        raise Http404()

def blog_subcategories(request, category_slug):
    if request.is_ajax():
        parent_category = BlogParentCategory.objects.get(slug=slugify(category_slug))
        if parent_category:
            resultCategoryList = ["All",]
            sub_categories = BlogCategory.objects.all().filter(parent_category=parent_category).values_list('title', flat=True)
            resultCategoryList = resultCategoryList + list(sub_categories)
            return HttpResponse(simplejson.dumps(resultCategoryList))
        return HttpResponse(simplejson.dumps("error"))
    else:
        raise Http404()

def get_vendors_allsub(request):
    url = request.path
    url += "all/"
    return HttpResponseRedirect(url)

def get_vendors_all(request):
    url = request.path
    url += "all/all/"
    return HttpResponseRedirect(url)

def is_valid_search_filter(filterstr):
    valid_filters = ['price', 'variety', 'quality', 'service', 'exchange', 'overall']
    if filterstr.lower() in valid_filters:
        return True
    return False

def get_vendors(request, parent_category_slug, sub_category_slug, template="blog/search_results.html"):
    if request.method == "GET":
        #parsedURL = urlparse.urlparse(request.path)
        #pathlist = parsedURL.path.split("/")
        filters = request.GET.get("filter", '')
        filter_arr = []
        if filters != '':
            filter_arr = filters.split('-')

        blog_parentcategory = None
        """
        /xyz/abc/ will return a list ["","xyz",abc",""] after parsing.
        2nd and 3rd element from last will be sub_category and parent_category respectively.
        """
        blog_parentcategory_slug = parent_category_slug#pathlist[-3]
        blog_parentcategory_title = _("All")

        if blog_parentcategory_slug.lower() != "all" and BlogParentCategory.objects.all().exists():
            try:
                blog_parentcategory = BlogParentCategory.objects.get(slug=slugify(blog_parentcategory_slug))
                blog_parentcategory_title = blog_parentcategory.title
            except BlogParentCategory.DoesNotExist:
                raise Http404()

        blog_subcategory = None
        blog_subcategory_slug = sub_category_slug#pathlist[-2]
        blog_subcategory_title = _("All")
        if blog_subcategory_slug.lower() != "all" and BlogCategory.objects.all().exists():
            try:
                blog_subcategory = BlogCategory.objects.get(slug=slugify(blog_subcategory_slug))
                blog_subcategory_title = blog_subcategory.title
            except BlogCategory.DoesNotExist:
                raise Http404()

        if blog_parentcategory_slug.lower() == "all" and blog_subcategory_slug.lower() == "all":
            results = BlogPost.objects.published()
        elif blog_parentcategory_slug.lower() != "all" and blog_subcategory_slug.lower() == "all":
            if blog_parentcategory:
                blog_subcategories = list(BlogCategory.objects.all().filter(parent_category=blog_parentcategory))
                results = BlogPost.objects.published().filter(categories__in=blog_subcategories).distinct()
        else:
            if blog_subcategory and blog_parentcategory:
                results = BlogPost.objects.published().filter(categories=blog_subcategory)
            else:
            	"""
                raise 404 error, in case categories are not present.
                """
                raise Http404()

        field_sum = ''
        if len(filter_arr) > 0:
            for i in range(len(filter_arr)):
                if is_valid_search_filter(filter_arr[i]):
                    if i == 0:
                        field_sum += filter_arr[i].lower()+'_average'
                    else:
                        field_sum += '+' + filter_arr[i].lower()+'_average'

        if field_sum != '': 
        	'''
        	If filters are apllied, order vendors by sum of the filter parameter values.
        	In case filter values are equal, order them as per their overall average.
        	For now tie between equal overall_average is not broken. To break add more parameters ahead in order of priority.
        	'''
        	filtered_results = results.extra(select={'fieldsum': field_sum}, order_by=('-fieldsum', '-overall_average',))
        else:
        	'''
        		In absence of any filters, order vendors by overall_average by default.
        	'''
        	filtered_results = results.order_by('-overall_average')

        settings.use_editable()
        page = request.GET.get("page", 1)
        per_page = settings.SEARCH_PER_PAGE
        max_paging_links = settings.MAX_PAGING_LINKS

        paginated = paginate(filtered_results, page, per_page, max_paging_links)
        context = {"results": paginated,
                    "parent_category": parent_category_slug,
                    "sub_category": sub_category_slug,
                    "parent_category_title": blog_parentcategory_title,
                    "sub_category_title": blog_subcategory_title
                    }
    	return render(request, template, context)
    else:
    	raise Http404()
