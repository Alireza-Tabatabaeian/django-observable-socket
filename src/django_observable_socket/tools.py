import re


def route_to_method_name(route: str) -> str:
    return 'on_{}'.format(re.sub(r'([a-z])([A-Z])', r'\1_\2', route).lower())

def result_is_successful(status: int) -> bool:
    return 200 <= status < 300
