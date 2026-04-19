
class KnowledgeBaseRouter:
    """
    Un router para controlar todas las operaciones de la base de datos
    en los modelos de ai_modules que son 'KnowledgeBase' (solo AIKnowledgeChunk por ahora).
    """
    route_app_labels = {'ai_modules'}
    knowledge_models = {'aiknowledgechunk'}

    def db_for_read(self, model, **hints):
        if model._meta.model_name in self.knowledge_models:
            return 'knowledge_base'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.model_name in self.knowledge_models:
            return 'knowledge_base'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Permitir relaciones si alguna de las tablas está en knowledge_base
        # (Aunque AIKnowledgeChunk tiene FK a AIAssistant, esto puede ser complejo.
        # Por ahora lo mantenemos simple: permitimos relaciones para lectura).
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if model_name in self.knowledge_models:
            return db == 'knowledge_base'
        return None
