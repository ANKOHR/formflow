"""Named parser and compiler errors with sentence-level source pointers."""

HONESTY = (
    "FormFlow uses deterministic rules over a declared phrase grammar. It does not use a language model, "
    "does not understand arbitrary English, and generates review demos, not production systems. "
    "Admin submissions are synthetic. Notification rules are definitions only and nothing is sent."
)


class FormFlowError(Exception):
    code = "FormFlowError"

    def __init__(self, message, *, line=None, sentence=None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.sentence = sentence

    def as_dict(self):
        return {
            "error": self.code,
            "message": self.message,
            "line": self.line,
            "sentence": self.sentence,
            "honesty": HONESTY,
        }


class UnsupportedPhraseError(FormFlowError):
    code = "UnsupportedPhraseError"


class AmbiguousPhraseError(FormFlowError):
    code = "AmbiguousPhraseError"


class MissingFormError(FormFlowError):
    code = "MissingFormError"


class DuplicateFieldError(FormFlowError):
    code = "DuplicateFieldError"


class UnknownFieldError(FormFlowError):
    code = "UnknownFieldError"


class WorkflowCycleError(FormFlowError):
    code = "WorkflowCycleError"


class InvalidProcessError(FormFlowError):
    code = "InvalidProcessError"
