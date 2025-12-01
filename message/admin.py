from django.contrib import admin
from django import forms
from .models import Message
from .services.message_service import MessageService


class MessageCreateAdminForm(forms.ModelForm):
	subject = forms.CharField(required=True)
	message = forms.CharField(required=True, widget=forms.Textarea)

	class Meta:
		model = Message
		fields = ['receiver', 'method']


class MessageChangeAdminForm(forms.ModelForm):
	class Meta:
		model = Message
		fields = ['sender', 'receiver', 'method', 'status', 'error_message']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
	list_display = ('id', 'sender', 'receiver', 'method', 'status', 'date')
	list_filter = ('method', 'status', 'date')
	search_fields = ('sender__username', 'receiver')
	readonly_fields = ('status', 'error_message', 'date', 'sender')

	def get_form(self, request, obj=None, **kwargs):
		if obj is None:
			kwargs['form'] = MessageCreateAdminForm
		else:
			kwargs['form'] = MessageChangeAdminForm
		return super().get_form(request, obj, **kwargs)

	def get_readonly_fields(self, request, obj=None):
		readonly = list(super().get_readonly_fields(request, obj))
		# If the message was sent, prevent editing of core fields
		if obj and obj.status != 'pending':
			for field in ['receiver', 'method']:
				if field not in readonly:
					readonly.append(field)
		return readonly

	def save_model(self, request, obj, form, change):
		if not change:
			# On create: use the logged-in admin as sender and send immediately
			obj.sender = request.user
			obj.save()

			# Attach ephemeral content and send via service
			subject = form.cleaned_data.get('subject')
			content = form.cleaned_data.get('message')
			MessageService.send_message(obj, content, subject)
		else:
			# On change: do not resend by default; just save allowed fields
			super().save_model(request, obj, form, change)

	def has_delete_permission(self, request, obj=None):
		# Disallow deletion from admin entirely
		return False
