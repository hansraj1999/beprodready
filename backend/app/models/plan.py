from enum import Enum


class Plan(str, Enum):
    free = "free"
    pro = "pro"
    lifetime = "lifetime"
