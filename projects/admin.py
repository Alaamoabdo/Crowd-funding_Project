from django.contrib import admin

from .models import Category, Comment, CommentReport, Donation, Project, ProjectImage, ProjectReport, Rating, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'category', 'target', 'status', 'featured', 'start_time', 'end_time')
    list_editable = ('featured',)
    list_filter = ('status', 'category')
    search_fields = ('title', 'details', 'creator__email')
    filter_horizontal = ('tags',)
    inlines = (ProjectImageInline,)


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('project', 'donor', 'amount', 'created_at')
    list_filter = ('created_at',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('project', 'author', 'created_at')
    search_fields = ('body', 'author__email', 'project__title')


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'score', 'created_at')
    list_filter = ('score',)


@admin.register(ProjectReport)
class ProjectReportAdmin(admin.ModelAdmin):
    list_display = ('project', 'reporter', 'reason', 'resolved', 'created_at')
    list_filter = ('resolved',)
    search_fields = ('reason', 'reporter__email', 'project__title')


@admin.register(CommentReport)
class CommentReportAdmin(admin.ModelAdmin):
    list_display = ('comment', 'reporter', 'reason', 'resolved', 'created_at')
    list_filter = ('resolved',)
    search_fields = ('reason', 'reporter__email', 'comment__body', 'comment__author__email')
