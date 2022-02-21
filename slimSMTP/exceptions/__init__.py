class AuthenticationError(BaseException):
	pass

class InvalidSender(BaseException):
	pass

class InvalidAddress(BaseException):
	pass

class SPFError(BaseException):
	pass

class EmailValidationError(BaseException):
	pass