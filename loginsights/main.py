class LogInsightsLogger:
    @staticmethod
    def get_logger():
        return LogInsightsLogger()
        
    def info(self, message): pass
    def error(self, message): pass
    def warning(self, message): pass
    def debug(self, message): pass
    def add_metric(self, name, data): pass
    
    @staticmethod
    def configure(config): pass 