from .pipeline import MoMoParser
from .models import ParseResult

# Module-level singleton — import and call parse() directly
_parser = MoMoParser()


def parse(sms_text: str, sender_id: str | None = None) -> ParseResult:
    """Parse a raw MoMo SMS. Thin wrapper around MoMoParser.parse()."""
    return _parser.parse(sms_text, sender_id)


__all__ = ["parse", "MoMoParser", "ParseResult"]
