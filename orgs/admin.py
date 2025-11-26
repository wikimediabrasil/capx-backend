from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from .models import (
	Organization,
	OrganizationType,
	Management,
	TagDiff,
	Document,
	OrganizationName,
)


class OrganizationNameInlineFormSet(BaseInlineFormSet):
	"""Ensure an English translation exists and cannot be deleted."""
	def clean(self):
		super().clean()
		english_present = False
		for form in self.forms:
			if not hasattr(form, 'cleaned_data'):
				continue
			# Determine language code from cleaned data or fall back to the instance.
			lang_code = form.cleaned_data.get('language_code')
			if not lang_code and hasattr(form, 'instance'):
				lang_code = getattr(form.instance, 'language_code', None)

			if form.cleaned_data.get('DELETE'):
				# Skip deleted forms (except we check 'en' below)
				if lang_code == 'en':
					raise ValidationError("The English (en) translation cannot be deleted. Delete the organization instead.")
				continue
			if lang_code == 'en':
				english_present = True
		if not english_present:
			raise ValidationError("An English (en) translation is required.")


class OrganizationNameInline(admin.TabularInline):
	model = OrganizationName
	formset = OrganizationNameInlineFormSet
	extra = 0
	min_num = 1
	verbose_name = "Localized name"
	verbose_name_plural = "Localized names"
	fields = ('language_code', 'name')
	readonly_fields = ()

	def get_readonly_fields(self, request, obj=None):
		# Prevent changing language_code for existing rows to avoid duplicates or confusion
		if obj:
			return ('language_code',)
		return self.readonly_fields


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
	inlines = [OrganizationNameInline]
	list_display = ('id', 'acronym', 'english_name', 'update_date')
	list_filter = ('type', 'managers')
	search_fields = ('acronym', 'i18n_names__name')
	ordering = ('acronym',)

	def english_name(self, obj: Organization):
		en = obj.i18n_names.filter(language_code='en').first()
		return en.name if en else ''
	english_name.short_description = 'English name'

	def save_model(self, request, obj, form, change):
		super().save_model(request, obj, form, change)


@admin.register(OrganizationType)
class OrganizationTypeAdmin(admin.ModelAdmin):
	list_display = ('id', 'type_code', 'type_name')
	search_fields = ('type_code', 'type_name')


@admin.register(Management)
class ManagementAdmin(admin.ModelAdmin):
	list_display = ('id', 'organization', 'user', 'joined_at')
	search_fields = ('organization__acronym', 'user__username')
	autocomplete_fields = ('organization', 'user')


@admin.register(TagDiff)
class TagDiffAdmin(admin.ModelAdmin):
	list_display = ('id', 'tag', 'creation_date')
	search_fields = ('tag',)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
	list_display = ('id', 'short_name', 'creation_date')
	search_fields = ('url',)

	def short_name(self, obj: Document):
		return obj.url.split('/')[-1]
	short_name.short_description = 'File'

# Do NOT register OrganizationName directly to avoid accidental deletions; managed via inline.
