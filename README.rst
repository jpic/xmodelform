django-xmodelform: customize the boundary between forms and models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This library provides an alternative ModelForm class, which compares to
Django's ModelForm as such:

- allows to register form field factories, to override the default form field
  generation logic (which is in the model field) on a per-project basis.

- allows form fields to encapsulate business logic happening in ``form.save()``
  they are saved.

These features have been introduced in django-autocomplete-light v2 and have
been maintained there for long enough. It is not provided anymore as part of
django-autocomplete-light as of V3 and is instead maintained here, because it
can serve for more than just autocompletes - have you ever thought "I wish I
could customize Django's ModelForm" ? If so, ``xmodelform.XModelForm`` might be
a solution.

Form field factory
==================

In Django, the model field class has the only callback to generate a form field
for a model field. The only way provided by Django to override that is by
defining an attribute with the model field's name in a ModelForm subclass.

While that works pretty well, this breaks the DRY principle if a project has
defined a set of app-provided form fields: the user has to re-define the form
field everywhere when it would be more efficient to re-define or enhance the
default model field logic to generate a form field.



Form field business logic
=========================

Many apps provide new related managers to extend your django models with. For
example, django-tagulous provides a TagField which abstracts an M2M relation
with the Tag model, django-gm2m provides a GM2MField which abstracts an
relation, django-taggit provides a TaggableManager which abstracts a relation
too, django-generic-m2m provides RelatedObjectsDescriptor which abstracts a
relation again.

While that works pretty well, it gets a bit complicated when it comes to
encapsulating the business logic for saving such data in a form object. This is
three-part problem:

- getting initial data,
- saving instance attributes,
- saving relations like reverse relations or many to many.

Django's ModelForm calls the form field's ``value_from_object()`` method to get
the initial data. ``FieldBusinessLogicModelForm`` tries the ``value_from_object()`` method
from the form field instead, if defined. Unlike the model field, the form field
doesn't know its name, so ``FieldBusinessLogicModelForm`` passes it when calling the form
field's ``value_from_object()`` method.

Django's ModelForm calls the form field's ``save_form_data()`` in two
occasions:

- in ``_post_clean()`` for model fields in ``Meta.fields``,
- in ``_save_m2m()`` for model fields in ``Meta.virtual_fields`` and
  ``Meta.many_to_many``, which then operate on an instance which as a PK.

If we just added ``save_form_data()`` to form fields like for
``value_from_object()`` then it would be called twice, once in
``_post_clean()`` and once in ``_save_m2m()``. Instead, ``FieldBusinessLogicModelForm``
would call the following methods from the form field, if defined:

- ``save_object_data()`` in ``_post_clean()``, to set object attributes for a
  given value,
- ``save_relation_data()`` in ``_save_m2m()``, to save relations for a given
  value.

For example:

- a generic foreign key only sets instance attributes, its form field would do
  that in ``save_object_data()``,
- a tag field saves relations, its form field would do that in
  ``save_relation_data()``.
