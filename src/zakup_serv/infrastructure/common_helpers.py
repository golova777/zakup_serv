from inspect import Signature


def normalize_signature(sig: Signature) -> Signature:
    """Убирает self для проверки сходства сигнатур"""

    params = list(sig.parameters.values())

    # если первый параметр называется self — просто выкидываем его
    if params and params[0].name == "self":
        params = params[1:]

    return Signature(
        parameters=params,
        return_annotation=sig.return_annotation,
    )
