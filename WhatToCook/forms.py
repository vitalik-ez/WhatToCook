from django import forms


def validate_file_extension(value):
    import os
    from django.core.exceptions import ValidationError
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = ['.jpg', '.png']
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension.')


class RecipeForm(forms.Form):
    #name_recipe = forms.CharField(max_length=50)
    #description = forms.CharField(max_length=250)
    #recipe = forms.CharField(max_length=500)
    photo = forms.ImageField(label="Фото")