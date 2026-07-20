"""Edit-profile form (YC-023.0).

URL fields accept only http(s) links; everything is optional. Rendering
relies on Jinja autoescaping, so stored text is always displayed safely.
"""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import Length, Optional, Regexp, URL

_HTTP_ONLY = Regexp(
    r"^https?://", message="Link must start with http:// or https://"
)


class EditProfileForm(FlaskForm):
    """All fields optional — an empty profile is a valid profile."""

    avatar_url = StringField(
        "Profile picture URL",
        validators=[Optional(), Length(max=500), URL(), _HTTP_ONLY],
    )
    bio = TextAreaField(
        "Bio",
        validators=[Optional(), Length(max=500,
            message="Bio must be 500 characters or fewer.")],
    )
    country = StringField("Country", validators=[Optional(), Length(max=56)])
    github_url = StringField(
        "GitHub URL",
        validators=[Optional(), Length(max=255), URL(), _HTTP_ONLY],
    )
    linkedin_url = StringField(
        "LinkedIn URL",
        validators=[Optional(), Length(max=255), URL(), _HTTP_ONLY],
    )
    website_url = StringField(
        "Website",
        validators=[Optional(), Length(max=255), URL(), _HTTP_ONLY],
    )
    submit = SubmitField("Save Profile")
