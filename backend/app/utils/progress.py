from django.core.cache import cache

class PipelineProgress:
    CACHE_KEY = 'hansard_pipeline_progress'
    
    @classmethod
    def update(cls, message, current=None, total=None):
        data = {
            'message': message,
            'current': current,
            'total': total,
        }
        cache.set(cls.CACHE_KEY, data, 300) # Expire in 5 mins
        
    @classmethod
    def get(cls):
        return cache.get(cls.CACHE_KEY)
    
    @classmethod
    def clear(cls):
        cache.delete(cls.CACHE_KEY)
