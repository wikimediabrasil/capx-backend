from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Case, When, F, Value, IntegerField
from django.utils.html import format_html

from skills.models import Skill
from translate.services import MetabaseClient


class SkillChoiceField(forms.ModelChoiceField):
	def __init__(self, *args, label_map=None, **kwargs):
		super().__init__(*args, **kwargs)
		self._label_map = label_map or {}

	def label_from_instance(self, obj):
		qid = getattr(obj, "skill_wikidata_item", "")
		return self._label_map.get(qid) or qid or str(obj)


def _build_label_map():
	qids = list(Skill.objects.order_by("pk").values_list("skill_wikidata_item", flat=True))
	if not qids:
		return {}
	client = MetabaseClient()
	terms = client.fetch_map_and_terms(qids)
	label_map = {}
	for qid, lang_map in terms.items():
		title = None
		# prefer English, else any available
		if "en" in lang_map:
			title = (lang_map.get("en") or {}).get("label")
		if not title:
			for entry in lang_map.values():
				title = entry.get("label")
				if title:
					break
		label_map[qid] = title or qid
	return label_map


class SkillCreateForm(forms.ModelForm):
	title = forms.CharField(label="Title", max_length=255)
	description = forms.CharField(label="Description", required=False, widget=forms.Textarea)
	lang = forms.CharField(label="Language", max_length=16, initial="en", help_text="Language code for the label/description (default: en)")

	class Meta:
		model = Skill
		fields = ["skill_wikidata_item", "skill_type", "title", "description", "lang"]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		label_map = _build_label_map()
		self.fields["skill_type"] = SkillChoiceField(
			queryset=Skill.objects.all(),
			required=False,
			label_map=label_map,
			label=self.fields["skill_type"].label,
			help_text=self.fields["skill_type"].help_text,
		)


class SkillEditForm(forms.ModelForm):
	class Meta:
		model = Skill
		fields = ["skill_wikidata_item", "skill_type"]

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		label_map = _build_label_map()
		self.fields["skill_type"] = SkillChoiceField(
			queryset=Skill.objects.all(),
			required=False,
			label_map=label_map,
			label=self.fields["skill_type"].label,
			help_text=self.fields["skill_type"].help_text,
		)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
	list_display = ("tree_title", "skill_wikidata_item")
	search_fields = ("skill_wikidata_item",)
	list_display_links = ("tree_title",)

	_label_map_cache = None

	def _get_label_map(self):
		if self._label_map_cache is None:
			self._label_map_cache = _build_label_map()
		return self._label_map_cache

	def tree_title(self, obj):
		# Compute depth: 0=root, 1=child, 2=grandchild
		depth = 0
		p = obj.skill_type
		while p:
			depth += 1
			p = getattr(p, "skill_type", None)
		indent = "&nbsp;&nbsp;&nbsp;" * depth + ("↳ " if depth else "")
		label_map = self._get_label_map()
		title = label_map.get(obj.skill_wikidata_item) or obj.skill_wikidata_item
		return format_html("{}{}", format_html(indent), title)
	tree_title.short_description = "Title"

	def get_form(self, request, obj=None, **kwargs):
		# Use custom form with title/description/lang on add view, and label-enhanced choices on edit
		if obj is None:
			defaults = {"form": SkillCreateForm}
		else:
			defaults = {"form": SkillEditForm}
		defaults.update(kwargs)
		return super().get_form(request, obj, **defaults)

	def get_queryset(self, request):
		qs = super().get_queryset(request).select_related("skill_type", "skill_type__skill_type")
		depth = Case(
			When(skill_type__isnull=True, then=Value(0)),
			When(skill_type__skill_type__isnull=True, then=Value(1)),
			default=Value(2),
			output_field=IntegerField(),
		)
		root_id = Case(
			When(skill_type__isnull=True, then=F("pk")),
			When(skill_type__skill_type__isnull=True, then=F("skill_type_id")),
			default=F("skill_type__skill_type_id"),
			output_field=IntegerField(),
		)
		qs = qs.annotate(_depth=depth, _root_id=root_id).order_by("_root_id", "_depth", "skill_type_id", "pk")
		# reset label map cache so it's fresh for current listing
		self._label_map_cache = None
		return qs

	def save_model(self, request, obj, form, change):
		# On create, push label/description to Metabase and link to Wikidata QID
		if not change:
			title = form.cleaned_data.get("title")
			description = form.cleaned_data.get("description")
			lang = form.cleaned_data.get("lang") or "en"
			qid = obj.skill_wikidata_item
			client = MetabaseClient()
			try:
				client.login_bot()
				mb_id = client.create_item(label=title, description=description, lang=lang, wikidata_qid=qid, editor_username=request.user.username)
				self.message_user(request, f"Created Metabase item {mb_id} and linked to {qid}.")
			except Exception as e:
				raise ValidationError({"__all__": f"Failed to create item on Metabase: {e}"})
		super().save_model(request, obj, form, change)