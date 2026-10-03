from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import ProtectedError, RestrictedError
from django.urls import reverse

GENERIC_FORM_TEMPLATE = 'inventory/generic-form.html'
GENERIC_DELETE_TEMPLATE = 'inventory/generic-delete.html'


def _build_form_context(form_class, redirect_url, instance=None):
    model = form_class.Meta.model
    verbose_name = model._meta.verbose_name.replace('_', ' ').title()
    verbose_name_plural = model._meta.verbose_name_plural.replace('_', ' ').title()

    if instance is not None:
        # Use the model's canonical display label so edit breadcrumbs match
        # detail pages (for example, an Area renders as "City - Area").
        object_label = str(instance)
        page_heading = f'Edit {object_label}'
        action_label = 'Edit'
    else:
        object_label = None
        page_heading = f'New {verbose_name}'
        action_label = 'New'

    breadcrumbs = [
        {'label': 'Home', 'url': reverse('dashboard')},
        {'label': verbose_name_plural, 'url': reverse(redirect_url)},
    ]

    if instance is not None:
        breadcrumbs.append({'label': object_label, 'url': None, 'active': False})

    breadcrumbs.append({'label': action_label, 'url': None, 'active': True})

    return {
        'model_verbose_name': verbose_name,
        'model_verbose_name_plural': verbose_name_plural,
        'home_label': 'Home',
        'breadcrumb_items': breadcrumbs,
        'page_heading': page_heading,
        'page_subtitle': f'Manage your {verbose_name_plural.lower()}',
    }


# ─────────────────────────────────────────────────────────────────────────────
# GENERIC CRUD HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def handle_create(request, form_class, redirect_url, template=GENERIC_FORM_TEMPLATE):
    """
    Generic create view.

    Args:
        request:      The HTTP request object.
        form_class:   The ModelForm class to instantiate (e.g. GeneralDirectorateForm).
        redirect_url: Named URL to redirect to on success AND for the Cancel link.
        template:     Template to render. Defaults to the shared generic-form.html.

    Context passed to template:
        form:                The form instance.
        model_verbose_name:  e.g. "general directorate" — used in the <h1> title.
        cancel_url:          Named URL for the Cancel link.

    Usage:
        def new_directorate(request):
            return handle_create(request, DirectorateForm, 'directorates-list')
    """
    form = form_class(request.POST or None)
    if form.is_valid():
        form.save()
        return redirect(redirect_url)

    context = _build_form_context(form_class, redirect_url)
    context.update({
        'form': form,
        'cancel_url': redirect_url,
    })
    return render(request, template, context)


def handle_update(request, form_class, redirect_url, pk,
                  template=GENERIC_FORM_TEMPLATE):
    """
    Generic update view.

    Args:
        request:      The HTTP request object.
        form_class:   The ModelForm class to instantiate.
        redirect_url: Named URL to redirect to on success AND for the Cancel link.
        pk:           Primary key of the object to update.
        template:     Template to render. Defaults to the shared generic-form.html.

    Context passed to template:
        form:    The bound form instance.
        object:  The model instance being updated — used in the <h1> title via
                 its __str__ method. The template checks {% if object %} to
                 distinguish create from update.
        cancel_url: Named URL for the Cancel link.

    Usage:
        def update_directorate(request, pk):
            return handle_update(request, DirectorateForm, 'directorates-list', pk)
    """
    model = form_class.Meta.model
    instance = get_object_or_404(model, pk=pk)
    form = form_class(request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        return redirect(redirect_url)

    context = _build_form_context(form_class, redirect_url, instance)
    context.update({
        'form': form,
        'object': instance,
        'cancel_url': redirect_url,
    })
    return render(request, template, context)


def handle_delete(request, model, redirect_url, pk,
                  template=GENERIC_DELETE_TEMPLATE,
                  protected_error_message=None):
    """
    Generic delete view with ProtectedError / RestrictedError handling.

    Args:
        request:                 The HTTP request object.
        model:                   The Django model class (e.g. GeneralDirectorate).
        redirect_url:            Named URL to redirect to on success AND for the Cancel link.
        pk:                      Primary key of the object to delete.
        template:                Template to render. Defaults to the shared generic-delete.html.
        protected_error_message: Custom error message when deletion is blocked.
                                 A sensible default is used if omitted.

    Context passed to template:
        object:        The model instance — used in the <h1> title via its __str__ method.
        error_message: Populated only when a ProtectedError / RestrictedError occurs.
        cancel_url:    Named URL for the Cancel / Go Back link.

    Usage:
        def delete_directorate(request, pk):
            return handle_delete(request, Directorate, 'directorates-list', pk)
    """
    instance = get_object_or_404(model, pk=pk)

    if request.method == 'POST':
        try:
            instance.delete()
            return redirect(redirect_url)
        except (ProtectedError, RestrictedError):
            error_message = protected_error_message or (
                f"Cannot delete this {model._meta.verbose_name} because it is still linked "
                f"to other records. Remove those dependencies first, then try again."
            )
            return render(request, template, {
                'object': instance,
                'error_message': error_message,
                'cancel_url': redirect_url,
            })

    return render(request, template, {
        'object': instance,
        'cancel_url': redirect_url,
    })
