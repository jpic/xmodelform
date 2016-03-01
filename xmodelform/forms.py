"""
tl;dr: See FutureModelForm's docstring for usage.

"""

from itertools import chain

from django import forms
from django.forms.models import ModelFormMetaclass
from django.utils import six


class FieldBusinessLogicModelForm(forms.ModelForm):
    """
    Allows form fields to encapsulate all business logic.

    Form fields may define new methods for FutureModelForm:

    - ``FormField.value_from_object(instance, name)`` should return the initial
      value to use in the form, overrides ``ModelField.value_from_object()``
      which is what ModelForm uses by default,
    - ``FormField.save_object_data(instance, name, value)`` should set instance
      attributes. Called by ``save()`` **before** writting the database, when
      ``instance.pk`` may not be set, it overrides
      ``ModelField.save_form_data()`` which is normally used in this occasion
      for non-m2m and non-virtual model fields.
    - ``FormField.save_relation_data(instance, name, value)`` should save
      relations required for value on the instance. Called by ``save()``
      **after** writting the database, when ``instance.pk`` is necessarely set,
      it overrides ``ModelField.save_form_data()`` which is normally used in
      this occasion for m2m and virtual model fields.

    For complete rationale, see this module's docstring.
    """

    def __init__(self, *args, **kwargs):
        """Override that uses a form field's ``value_from_object()``."""
        super(FutureModelForm, self).__init__(*args, **kwargs)

        for name, field in self.fields.items():
            if not hasattr(field, 'value_from_object'):
                continue

            self.initial[name] = field.value_from_object(self.instance, name)

    def _post_clean(self):
        """Override that uses the form field's ``save_object_data()``."""
        super(FutureModelForm, self)._post_clean()

        for name, field in self.fields.items():
            if not hasattr(field, 'save_object_data'):
                continue

            field.save_object_data(
                self.instance,
                name,
                self.cleaned_data.get(name, None),
            )

    def _save_m2m(self):  # noqa
        """Override that uses the form field's ``save_object_data()``."""
        cleaned_data = self.cleaned_data
        exclude = self._meta.exclude
        fields = self._meta.fields
        opts = self.instance._meta

        # Added to give the field a chance to do the work
        handled = []
        for name, field in self.fields.items():
            if not hasattr(field, 'save_relation_data'):
                continue

            field.save_relation_data(
                self.instance,
                name,
                cleaned_data[name]
            )

            handled.append(name)

        # Note that for historical reasons we want to include also
        # virtual_fields here. (GenericRelation was previously a fake
        # m2m field).
        for f in chain(opts.many_to_many, opts.virtual_fields):
            # Added to give the form field a chance to do the work
            if f.name in handled:
                continue

            if not hasattr(f, 'save_form_data'):
                continue
            if fields and f.name not in fields:
                continue
            if exclude and f.name in exclude:
                continue
            if f.name in cleaned_data:
                f.save_form_data(self.instance, cleaned_data[f.name])

    def save(self, commit=True):
        """Backport from Django 1.9+ for 1.8."""
        if self.errors:
            raise ValueError(
                "The %s could not be %s because the data didn't validate." % (
                    self.instance._meta.object_name,
                    'created' if self.instance._state.adding else 'changed',
                )
            )
        if commit:
            # If committing, save the instance and the m2m data immediately.
            self.instance.save()
            self._save_m2m()
        else:
            # If not committing, add a method to the form to allow deferred
            # saving of m2m data.
            self.save_m2m = self._save_m2m
        return self.instance


class FutureFormMetaclass(ModelFormMetaclass):
    factories = []

    @classmethod
    def get_meta(cls, name, bases, attrs):
        meta = attrs.get('Meta', None)

        # Maybe the parent has a meta ?
        if meta is None:
            for parent in bases + type(cls).__mro__:
                meta = getattr(parent, 'Meta', None)

                if meta is not None:
                    break

        return meta

    @classmethod
    def get_fields(cls, meta):
        fields = getattr(meta, 'fields', None)

        if fields == '__all__':
            return [f for f in meta.model._meta.fields]
        elif fields is None:
            exclude = getattr(meta, 'exclude', None)

            if exclude is None:
                raise Exception()

            return [f for f in meta.model._meta.fields
                    if f.name not in exclude]

        return meta.model._meta.fields

    def __new__(cls, name, bases, attrs):
        meta = cls.get_meta(name, bases, attrs)

        if meta is not None:
            for field in cls.get_fields(meta):
                if field.name in attrs:
                    # Skip manually declared field
                    continue

                for factory in cls.factories:
                    result = factory(meta, field)

                    if result is not None:
                        attrs[field.name] = result

        new_class = super(FutureFormMetaclass, cls).__new__(cls, name, bases,
                attrs)

        return new_class


class XModelForm(six.with_metaclass(FieldFactoryMetaclass,
                                    FieldBusinessLogicModelForm)):

    @classmethod
    def field_factory(cls, meta, field):
        autocomplete_urls = getattr(meta, 'autocomplete_urls', {})

        if field.name in autocomplete_urls:
            import ipdb; ipdb.set_trace()
