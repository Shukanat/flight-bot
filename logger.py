import logging
 
from opencensus.trace import config_integration
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer

config_integration.trace_integrations(["logging", "requests"])

class AzureLogger:

    def __init__(self, exporter, handler) -> None:
        handler.setFormatter(logging.Formatter("%(traceId)s %(spanId)s %(message)s"))
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(handler)
        self.tracer = Tracer(exporter=exporter, sampler=ProbabilitySampler(1.0))