import os

from hypothesis import HealthCheck, settings

settings.register_profile("default", deadline=None,
                          suppress_health_check=[HealthCheck.too_slow])
settings.register_profile("thorough", max_examples=1000, deadline=None,
                          suppress_health_check=[HealthCheck.too_slow])
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "default"))
