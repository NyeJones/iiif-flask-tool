from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

class SearchForm(FlaskForm):
	"""
	This class defines a search form used for submitting search queries.
	"""
	searched = StringField('searched', validators=[DataRequired(), Length(max=100)])
	submit = SubmitField('Submit')
