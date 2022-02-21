from .mail import Mail as Mail
from .spam import (
	validate_top_level_domain as validate_top_level_domain,
	validate_email_address as validate_email_address,
	get_mail_servers as get_mail_servers,
	spammer as spammer,
	is_spammer as is_spammer
)
from .helpers import clean_email as clean_email